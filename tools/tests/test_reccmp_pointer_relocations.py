import struct
import unittest
from types import SimpleNamespace
from reccmp.formats.pe import PEImage
from reccmp.formats.exceptions import InvalidVirtualAddressError


def block(entries, page=0x1000, size=None):
    payload = struct.pack('<' + 'H' * len(entries), *entries)
    return struct.pack('<II', page, len(payload) + 8 if size is None else size) + payload


def parse(data, directory_offset=0, directory_size=None, virtual_remaining=None,
          lower=0x401000, upper=0x402000, absent=False, bad_seek=False):
    directory_size = len(data) - directory_offset if directory_size is None else directory_size
    region = SimpleNamespace(virtual_address=0x403000 + directory_offset, virtual_size=directory_size)

    def seek(address):
        if bad_seek:
            raise InvalidVirtualAddressError('test')
        offset = address - 0x403000
        view = memoryview(data)[offset:]
        return view, len(view) if virtual_remaining is None else virtual_remaining

    image = SimpleNamespace(
        imagebase=0x400000,
        get_data_directory_region=lambda _: None if absent else region,
        seek=seek,
        is_valid_vaddr=lambda address: lower <= address < upper,
    )
    return PEImage.pointer_relocations.func(image)


class TypedRelocationTests(unittest.TestCase):
    def test_highlow(self):
        self.assertEqual(parse(block([0x3020, 0])), {0x401020})

    def test_highadj_partner_is_raw_data_for_any_apparent_type(self):
        for partner in [0, 0x3040, 0x4040, 0xffff, 0xa040]:
            with self.subTest(partner=partner):
                self.assertEqual(parse(block([0x4020, partner, 0x3060, 0])), {0x401060})

    def test_supported_mixed_types(self):
        self.assertEqual(parse(block([0x1020, 0x2022, 0x3024, 0])), {0x401024})

    def test_unsupported_types_fail_closed(self):
        for kind in range(5, 16):
            with self.subTest(kind=kind):
                self.assertEqual(parse(block([0x3020, (kind << 12) | 0x40])), set())

    def test_terminal_highadj(self):
        self.assertEqual(parse(block([0x3020, 0x4022])), set())

    def test_later_bad_block_clears_valid_prefix(self):
        self.assertEqual(parse(block([0x3020, 0]) + block([0x4020])), set())

    def test_short_header(self):
        self.assertEqual(parse(block([0x3020, 0]) + b'\x01\x00'), set())

    def test_bad_sizes(self):
        for raw in [block([], size=6), block([0x3020], size=11) + b'\x00',
                    block([0x3020], size=12), block([], size=0)]:
            with self.subTest(raw=raw):
                self.assertEqual(parse(raw), set())

    def test_zero_terminator_and_nonzero_tail(self):
        self.assertEqual(parse(block([0x3020, 0]) + bytes(8)), {0x401020})
        self.assertEqual(parse(block([0x3020, 0]) + bytes(8) + b'\x01'), set())

    def test_complete_field_address_validation(self):
        self.assertEqual(parse(block([0x3ffc, 0])), {0x401ffc})
        self.assertEqual(parse(block([0x3fff, 0])), set())

    def test_page_alignment(self):
        self.assertEqual(parse(block([0x3020, 0], page=0x1001)), set())

    def test_block_start_alignment(self):
        self.assertEqual(parse(block([0x3020]) + block([0x3040, 0])), set())

    def test_last_block_may_end_without_padding(self):
        self.assertEqual(parse(block([0x3020])), {0x401020})

    def test_duplicate_and_partial_overlaps_fail_closed(self):
        for entries in [[0x3020, 0x3020], [0x3020, 0x1022], [0x1022, 0x3020],
                        [0x3020, 0x4020, 0, 0]]:
            with self.subTest(entries=entries):
                self.assertEqual(parse(block(entries)), set())

    def test_adjacent_nonoverlapping_fields(self):
        self.assertEqual(parse(block([0x1020, 0x2022, 0x3024, 0])), {0x401024})

    def test_directory_in_middle_of_section(self):
        prefix = block([0x3090, 0])
        active = block([0x3020, 0])
        self.assertEqual(parse(prefix + active, directory_offset=len(prefix), directory_size=len(active)), {0x401020})

    def test_fake_highlow_outside_declared_directory(self):
        active = block([0x3020, 0])
        self.assertEqual(parse(active + block([0x3090, 0]), directory_size=len(active)), {0x401020})

    def test_declared_directory_truncates_block(self):
        self.assertEqual(parse(block([0x3020, 0]), directory_size=10), set())

    def test_declared_directory_larger_than_physical_data(self):
        self.assertEqual(parse(block([0x3020, 0]), directory_size=16, virtual_remaining=32), set())

    def test_declared_directory_larger_than_virtual_extent(self):
        self.assertEqual(parse(block([0x3020, 0]), directory_size=12, virtual_remaining=10), set())

    def test_directory_absent_empty_negative_or_invalid(self):
        for kwargs in [dict(absent=True), dict(directory_size=0), dict(directory_size=-1), dict(bad_seek=True)]:
            with self.subTest(kwargs=kwargs):
                self.assertEqual(parse(block([0x3020, 0]), **kwargs), set())


if __name__ == '__main__':
    unittest.main()
