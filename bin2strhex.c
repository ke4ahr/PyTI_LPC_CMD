/*
 * bin2strhex.c -- Convert binary file to comma-separated hex strings.
 *
 * Usage: bin2strhex [OPTIONS] bin_file
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define DEFAULT_PREFIX    "0x"
#define DEFAULT_WORD_SIZE 1
#define DEFAULT_ENDIAN    0  /* 0 = little, 1 = big */

static void usage(const char *prog)
{
    fprintf(stderr,
        "Usage: %s [OPTIONS] bin_file\n"
        "\n"
        "Options:\n"
        "  --endian {little,lsb,big,msb}  Byte order for multi-byte words (default: little)\n"
        "  --word-size {1,2,4}            Word size in bytes (default: 1)\n"
        "  --prefix TEXT                  Hex prefix string (default: 0x)\n"
        "  --no-prefix                    Omit hex prefix\n"
        "  -o, --output FILE              Output file (default: stdout)\n"
        "  -h, --help                     Show this help\n",
        prog);
}

static int parse_word_size(const char *s)
{
    int v = atoi(s);
    if (v == 1 || v == 2 || v == 4)
        return v;
    fprintf(stderr, "Error: --word-size must be 1, 2, or 4\n");
    exit(1);
}

static int parse_endian(const char *s)
{
    if (strcmp(s, "little") == 0 || strcmp(s, "lsb") == 0)
        return 0;
    if (strcmp(s, "big") == 0 || strcmp(s, "msb") == 0)
        return 1;
    fprintf(stderr, "Error: --endian must be little, lsb, big, or msb\n");
    exit(1);
}

int main(int argc, char *argv[])
{
    const char *bin_file   = NULL;
    const char *out_file   = NULL;
    const char *prefix     = DEFAULT_PREFIX;
    int         word_size  = DEFAULT_WORD_SIZE;
    int         big_endian = DEFAULT_ENDIAN;
    int         no_prefix  = 0;

    /* Parse arguments */
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--endian") == 0) {
            if (++i >= argc) { fprintf(stderr, "Error: --endian requires a value\n"); return 1; }
            big_endian = parse_endian(argv[i]);
        } else if (strncmp(argv[i], "--endian=", 9) == 0) {
            big_endian = parse_endian(argv[i] + 9);
        } else if (strcmp(argv[i], "--word-size") == 0) {
            if (++i >= argc) { fprintf(stderr, "Error: --word-size requires a value\n"); return 1; }
            word_size = parse_word_size(argv[i]);
        } else if (strncmp(argv[i], "--word-size=", 12) == 0) {
            word_size = parse_word_size(argv[i] + 12);
        } else if (strcmp(argv[i], "--prefix") == 0) {
            if (++i >= argc) { fprintf(stderr, "Error: --prefix requires a value\n"); return 1; }
            prefix = argv[i];
        } else if (strncmp(argv[i], "--prefix=", 9) == 0) {
            prefix = argv[i] + 9;
        } else if (strcmp(argv[i], "--no-prefix") == 0) {
            no_prefix = 1;
        } else if (strcmp(argv[i], "-o") == 0 || strcmp(argv[i], "--output") == 0) {
            if (++i >= argc) { fprintf(stderr, "Error: -o/--output requires a value\n"); return 1; }
            out_file = argv[i];
        } else if (strncmp(argv[i], "--output=", 9) == 0) {
            out_file = argv[i] + 9;
        } else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
            return 0;
        } else if (argv[i][0] == '-') {
            fprintf(stderr, "Error: unknown option: %s\n", argv[i]);
            return 1;
        } else {
            if (bin_file) { fprintf(stderr, "Error: unexpected argument: %s\n", argv[i]); return 1; }
            bin_file = argv[i];
        }
    }

    if (!bin_file) {
        usage(argv[0]);
        return 1;
    }

    if (no_prefix)
        prefix = "";

    /* Read input file */
    FILE *fin = fopen(bin_file, "rb");
    if (!fin) {
        perror(bin_file);
        return 1;
    }

    fseek(fin, 0, SEEK_END);
    long file_size = ftell(fin);
    rewind(fin);

    /* Pad to word boundary */
    long padded_size = file_size;
    int  tail        = (int)(file_size % word_size);
    if (tail != 0) {
        fprintf(stderr,
            "Warning: file size %ld not a multiple of word size %d; "
            "last %d byte(s) padded with 0x00\n",
            file_size, word_size, word_size - tail);
        padded_size = file_size + (word_size - tail);
    }

    unsigned char *data = calloc((size_t)padded_size, 1);
    if (!data) {
        fprintf(stderr, "Error: out of memory\n");
        fclose(fin);
        return 1;
    }

    if (fread(data, 1, (size_t)file_size, fin) != (size_t)file_size) {
        fprintf(stderr, "Error: failed to read %s\n", bin_file);
        free(data);
        fclose(fin);
        return 1;
    }
    fclose(fin);

    /* Open output */
    FILE *fout = stdout;
    if (out_file) {
        fout = fopen(out_file, "w");
        if (!fout) {
            perror(out_file);
            free(data);
            return 1;
        }
    }

    /* Emit comma-separated hex tokens */
    long word_count = padded_size / word_size;
    int  hex_digits = word_size * 2;

    for (long w = 0; w < word_count; w++) {
        const unsigned char *chunk = data + w * word_size;

        /* Assemble word value according to endianness */
        unsigned long value = 0;
        if (big_endian) {
            for (int b = 0; b < word_size; b++)
                value = (value << 8) | chunk[b];
        } else {
            for (int b = word_size - 1; b >= 0; b--)
                value = (value << 8) | chunk[b];
        }

        if (w > 0)
            fputc(',', fout);

        fprintf(fout, "%s%0*lX", prefix, hex_digits, value);
    }

    fputc('\n', fout);

    if (out_file)
        fclose(fout);

    free(data);
    return 0;
}
