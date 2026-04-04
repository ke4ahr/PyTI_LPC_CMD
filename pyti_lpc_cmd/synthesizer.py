# Copyright (C) 2026 Kris Kirby, KE4AHR
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""LPC speech synthesizer -- excitation, 10th-order lattice filter, interpolation.

Spec references: sec. 4.1-sec. 4.5, sec. 10.3, sec. 13.3
"""

from __future__ import annotations

from typing import List

from .bitstream import BitstreamReader
from .chip_params import ChipParams
from .frame_decoder import LPCFrame, decode_frame


class LPCSynthesizer:
    """Decodes an LPC bitstream and produces floating-point 8 kHz PCM samples.

    All state is reset at the start of each call to synthesize().
    """

    LPC_SAMPLE_RATE: int = 8000
    FRAME_TIME: float = 0.025         # 25 ms per frame
    SAMPLES_PER_FRAME: int = 200      # 8000 x 0.025
    INTERP_STEPS: int = 8
    # Interpolation shifts per sub-step (spec sec. 4.3)
    INTERP_SHIFTS: List[int] = [0, 3, 3, 3, 2, 2, 1, 1]
    K_SCALE: float = 512.0
    OUTPUT_GAIN: float = 1.5          # post-filter gain stage (spec sec. 4.4)

    # Sub-step boundary: every SAMPLES_PER_FRAME // INTERP_STEPS = 25 samples
    _SUBSTEP: int = SAMPLES_PER_FRAME // INTERP_STEPS  # 25

    def __init__(self) -> None:
        self._x: List[float] = [0.0] * 10   # lattice filter delay states
        self._synth_rand: int = 1             # LFSR seed (spec sec. 4.2)
        self._period_counter: int = 0         # chirp position counter

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def synthesize(
        self,
        data: bytes,
        chip: ChipParams,
        use_interp: bool = True,
        max_frames: int = 200,
        verbose: bool = False,
        use_loopguard: bool = True,
    ) -> List[float]:
        """Decode an LPC bitstream and return a list of 8 kHz float samples.

        Samples are nominally in the range [-1.5, 1.5] after the 1.5x gain
        stage.  Callers should clamp/scale before writing to audio files.

        Args:
            data: Raw LPC bitstream bytes.
            chip: Chip parameter tables.
            use_interp: Enable parameter interpolation (default True).
            max_frames: Infinite-loop guard limit (spec sec. 4.5).
            verbose: Print per-frame debug info.
            use_loopguard: Enable the infinite-loop guard (default True).
                When False, the synthesizer will not halt on silence-only
                inputs after max_frames frames.

        Returns:
            List of floating-point samples at 8000 Hz.
        """
        # Reset state
        self._x = [0.0] * 10
        self._synth_rand = 1
        self._period_counter = 0

        reader = BitstreamReader(data, reverse_bits=True)
        samples: List[float] = []

        prev_k: List[int] = [0] * 10
        cur_energy: int = 0
        cur_period: int = 0
        cur_k: List[int] = [0] * 10

        last_voiced: bool = False
        last_silence: bool = True    # start in silence
        ending_countdown: int = -1
        frame_count: int = 0

        while True:
            # ---- Decode or fabricate frame ----
            if ending_countdown < 0:
                frame = decode_frame(reader, chip, prev_k)
            else:
                frame = LPCFrame(is_silence=True, energy=0, period=0)

            # ---- Handle stop frame ----
            if frame.is_stop and ending_countdown < 0:
                ending_countdown = 2
                frame = LPCFrame(is_silence=True, energy=0, period=0)

            # ---- Determine from/target parameter sets ----
            from_energy: int = cur_energy
            from_period: int = cur_period
            from_k: List[int] = list(cur_k)

            tgt_energy: int = frame.energy
            tgt_period: int = frame.period
            tgt_k: List[int] = list(frame.k)

            # First frame: snap immediately to target (no interpolation ramp)
            if frame_count == 0:
                cur_energy = tgt_energy
                cur_period = tgt_period
                cur_k = list(tgt_k)
                from_energy = cur_energy
                from_period = cur_period
                from_k = list(cur_k)

            # ---- Determine whether to skip interpolation ----
            # Skip if voicing mode or silence state changes (spec sec. 4.3)
            now_voiced: bool = cur_period != 0
            now_silence: bool = cur_energy == 0
            skip_interp: bool = (
                not use_interp
                or (now_voiced != last_voiced)
                or (now_silence != last_silence)
            )

            # ---- Infinite-loop guard (spec sec. 4.5) ----
            if (
                use_loopguard
                and frame_count >= max_frames
                and frame.energy_idx == 0
                and tgt_energy == 0
                and tgt_period == 0
                and not frame.repeat
                and ending_countdown == -1
            ):
                if verbose:
                    print(f"[synth] infinite loop guard triggered at frame {frame_count}")
                break

            if verbose:
                print(
                    f"[synth] frame {frame_count:3d}: "
                    f"energy={tgt_energy:3d} period={tgt_period:3d} "
                    f"repeat={int(frame.repeat)} "
                    f"silence={int(frame.is_silence)} stop={int(frame.is_stop)} "
                    f"skip_interp={int(skip_interp)}"
                )

            # ---- Generate 200 samples for this frame ----
            interp_idx: int = 0
            # Working copies used for synthesis within this frame
            synth_energy: int = from_energy
            synth_period: int = from_period
            synth_k: List[int] = list(from_k)

            for s in range(self.SAMPLES_PER_FRAME):
                # Interpolation update -- 8 times per frame, at samples 25,50,...,175
                # (i.e., s > 0 and s is a multiple of 25)
                if s > 0 and (s % self._SUBSTEP) == 0:
                    if not skip_interp and interp_idx < self.INTERP_STEPS:
                        shift = self.INTERP_SHIFTS[interp_idx]
                        if shift > 0:
                            cur_energy = cur_energy + ((tgt_energy - cur_energy) >> shift)
                            cur_period = cur_period + ((tgt_period - cur_period) >> shift)
                            for n in range(10):
                                cur_k[n] = cur_k[n] + ((tgt_k[n] - cur_k[n]) >> shift)
                        # Per spec sec. 4.3 quirk: after interpolation the 'from_' values
                        # are used for actual synthesis, not the interpolated cur_ values.
                        # This matches the original chip behavior at frame boundaries.
                        synth_energy = from_energy
                        synth_period = from_period
                        synth_k = list(from_k)
                    interp_idx += 1

                # ---- Excitation ----
                u10 = self._excitation(synth_energy, synth_period, chip.chirp)

                # ---- Lattice filter ----
                sample = self._lattice_filter(u10, synth_k)

                samples.append(sample * self.OUTPUT_GAIN)

            # ---- Update state for next frame ----
            last_voiced = cur_period != 0
            last_silence = cur_energy == 0
            cur_energy = tgt_energy
            cur_period = tgt_period
            cur_k = list(tgt_k)
            prev_k = list(tgt_k)
            frame_count += 1

            # ---- Ending drain countdown ----
            if ending_countdown > 0:
                ending_countdown -= 1
                if ending_countdown == 0:
                    break

        return samples

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _excitation(
        self,
        energy: int,
        period: int,
        chirp: List[int],
    ) -> float:
        """Generate one excitation sample (voiced chirp or unvoiced LFSR noise).

        Spec sec. 4.2, sec. 13.3.
        """
        if period > 0:
            # ---- Voiced: chirp waveform ----
            if self._period_counter < 41:
                raw = chirp[self._period_counter]
                # Interpret uint8 as signed int8 (spec sec. 4.2, sec. 13.3)
                signed_val = raw if raw < 128 else raw - 256
                u10 = (signed_val / 256.0) * (energy / 256.0)
            else:
                u10 = 0.0

            # Advance or reset the chirp period counter
            if self._period_counter >= period - 1:
                self._period_counter = 0
            else:
                self._period_counter += 1
        else:
            # ---- Unvoiced: LFSR pseudo-random noise ----
            self._synth_rand = (
                (self._synth_rand >> 1)
                ^ (0xB800 if (self._synth_rand & 1) else 0)
            ) & 0xFFFF
            noise = energy if (self._synth_rand & 1) else -energy
            u10 = noise / 2048.0

        return u10

    def _lattice_filter(self, u10: float, k: List[int]) -> float:
        """10th-order lattice filter.

        K coefficient values are pre-scaled by 512 (spec sec. 4.4).
        Computes the forward path (excitation->output) then the reverse
        path (update delay states).

        Spec sec. 4.4, sec. 10.3.
        """
        s = self.K_SCALE
        x = self._x  # reference to mutable state list

        # ---- Forward path: u10 -> u9 -> ... -> u0 ----
        u9  = u10 - (k[9] / s) * x[9]
        u8  = u9  - (k[8] / s) * x[8]
        u7  = u8  - (k[7] / s) * x[7]
        u6  = u7  - (k[6] / s) * x[6]
        u5  = u6  - (k[5] / s) * x[5]
        u4  = u5  - (k[4] / s) * x[4]
        u3  = u4  - (k[3] / s) * x[3]
        u2  = u3  - (k[2] / s) * x[2]
        u1  = u2  - (k[1] / s) * x[1]
        u0  = u1  - (k[0] / s) * x[0]

        # Clamp output to prevent runaway (spec sec. 4.4, sec. 8.3)
        u0 = max(-1.0, min(1.0, u0))

        # ---- Reverse path: update delay states ----
        x[9] = x[8] + (k[8] / s) * u8
        x[8] = x[7] + (k[7] / s) * u7
        x[7] = x[6] + (k[6] / s) * u6
        x[6] = x[5] + (k[5] / s) * u5
        x[5] = x[4] + (k[4] / s) * u4
        x[4] = x[3] + (k[3] / s) * u3
        x[3] = x[2] + (k[2] / s) * u2
        x[2] = x[1] + (k[1] / s) * u1
        x[1] = x[0] + (k[0] / s) * u0
        x[0] = u0

        return u0
