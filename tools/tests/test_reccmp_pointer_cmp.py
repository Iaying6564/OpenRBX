import unittest
import capstone
from reccmp.compare.asm.parse import ParseAsm
from reccmp.compare.asm.replacement import create_name_lookup
from reccmp.compare.db import EntityDb
from reccmp.types import ImageId, EntityType

class PointerCompareTests(unittest.TestCase):

    def setUp(self):
        self.db = EntityDb()
        self.add('array', 4096, 8192, 12, EntityType.DATA)
        self.add('text', 12288, 16384, 24, EntityType.STRING)

    def add(self, name, a, b, size, kind):
        values = {'name': name, 'type': kind, 'orig_size': size, 'recomp_size': size}
        self.db.bulk_insert(ImageId.ORIG, [(a, values)])
        self.db.bulk_insert(ImageId.RECOMP, [(b, values)])
        self.db.bulk_match([(a, b)])

    def asm(self, img, value, relocated=True, reloc_at=None, instruction=None):
        lookup = create_name_lookup(self.db, img, lambda _: None, lambda _, off: f'+{off}')
        address_lookup = create_name_lookup(self.db, img, lambda _: None, lambda _, off: f'+{off}', address_only=True)
        p = ParseAsm(addr_test=lambda *_: True, name_lookup=lookup, address_lookup=address_lookup, pointer_reloc_test=(lambda addr: addr == (20482 if reloc_at is None else reloc_at)) if relocated is True else None, reloc_test=(lambda addr: addr == (20482 if reloc_at is None else reloc_at)) if relocated is not None else None)
        if relocated is False:
            p.reloc_test = lambda _: False
        return p.sanitize(instruction or (20480, 6, 'cmp', f'esi, {value:#x}'))[1]

    def test_untyped_legacy_relocation_cannot_enable_new_lookup(self):
        ordinary = create_name_lookup(self.db, ImageId.ORIG, lambda _: None, lambda _, off: f'+{off}')
        address = create_name_lookup(self.db, ImageId.ORIG, lambda _: None, lambda _, off: f'+{off}', address_only=True)
        parser = ParseAsm(name_lookup=ordinary, address_lookup=address, reloc_test=lambda _: True)
        self.assertEqual(parser.sanitize((20480, 6, 'cmp', 'esi, 0x100c'))[1], 'esi, 0x100c')

    def test_matched_one_past_is_named_and_equal(self):
        self.assertEqual(self.asm(ImageId.ORIG, 4108), 'esi, array+12 (OFFSET)')
        self.assertEqual(self.asm(ImageId.ORIG, 4108), self.asm(ImageId.RECOMP, 8204))

    def test_matched_string_interior_is_named_and_equal(self):
        self.assertEqual(self.asm(ImageId.ORIG, 12300), 'esi, text+12 (OFFSET)')
        self.assertEqual(self.asm(ImageId.ORIG, 12300), self.asm(ImageId.RECOMP, 16396))

    def test_unrelocated_numeric_new_cases_stay_literals(self):
        self.assertEqual(self.asm(ImageId.ORIG, 4108, False), 'esi, 0x100c')
        self.assertEqual(self.asm(ImageId.ORIG, 12300, False), 'esi, 0x300c')

    def test_missing_relocations_do_not_enable_new_cases(self):
        self.assertEqual(self.asm(ImageId.ORIG, 4108, None), 'esi, 0x100c')

    def test_wrong_relocation_field_does_not_enable(self):
        self.assertEqual(self.asm(ImageId.ORIG, 4108, reloc_at=20481), 'esi, 0x100c')

    def test_arbitrary_beyond_end_not_normalized(self):
        self.assertEqual(self.asm(ImageId.ORIG, 4109), 'esi, 0x100d')
        self.assertNotEqual(self.asm(ImageId.ORIG, 4109), self.asm(ImageId.RECOMP, 8205))

    def test_different_string_offsets_remain_different(self):
        self.assertNotEqual(self.asm(ImageId.ORIG, 12299), self.asm(ImageId.RECOMP, 16396))

    def test_different_bases_remain_different(self):
        self.add('other', 4352, 8448, 12, EntityType.DATA)
        self.assertNotEqual(self.asm(ImageId.ORIG, 4108), self.asm(ImageId.RECOMP, 8460))

    def test_exact_next_entity_wins_over_previous_end(self):
        self.add('next', 4108, 8204, 4, EntityType.DATA)
        self.assertEqual(self.asm(ImageId.ORIG, 4108), 'esi, next (DATA)')

    def test_string_end_not_treated_as_interior(self):
        self.assertEqual(self.asm(ImageId.ORIG, 12312), 'esi, 0x3018')

    def test_unmatched_endpoint_not_named(self):
        self.db.bulk_insert(ImageId.ORIG, [(24576, {'name': 'unmatched', 'type': EntityType.DATA, 'orig_size': 12})])
        self.assertEqual(self.asm(ImageId.ORIG, 24588), 'esi, 0x600c')

    def test_ordinary_lookup_boundaries_unchanged(self):
        lookup = create_name_lookup(self.db, ImageId.ORIG, lambda _: None, lambda _, off: f'+{off}')
        self.assertIsNone(lookup(4108))
        self.assertIsNone(lookup(12300))

    def test_legacy_three_argument_callback_compatible(self):

        def callback(addr, exact=False, indirect=False):
            return 'legacy'
        p = ParseAsm(name_lookup=callback, pointer_reloc_test=lambda addr: addr == 20482)
        self.assertEqual(p.sanitize((20480, 6, 'cmp', 'esi, 0x100c'))[1], 'esi, legacy')

    def test_memory_displacement_relocation_with_imm8_not_pointer(self):
        self.add('smalltext', 32, 128, 24, EntityType.STRING)
        instruction = next(capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32).disasm_lite(bytes.fromhex('833d001000002c'), 20480))
        self.assertTrue(self.asm(ImageId.ORIG, 44, reloc_at=20482, instruction=instruction).endswith(', 0x2c'))

    def test_memory_displacement_relocation_with_imm16_not_pointer(self):
        instruction = next(capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32).disasm_lite(bytes.fromhex('66813d001000000c30'), 20480))
        self.assertTrue(self.asm(ImageId.ORIG, 12300, reloc_at=20483, instruction=instruction).endswith(', 0x300c'))

    def test_register_imm16_excluded_even_with_misleading_relocation(self):
        self.assertEqual(self.asm(ImageId.ORIG, 4108, reloc_at=20481, instruction=(20480, 5, 'cmp', 'si, 0x100c')), 'si, 0x100c')

    def test_small_instruction_excluded_even_with_misleading_relocation(self):
        self.assertEqual(self.asm(ImageId.ORIG, 4108, reloc_at=20479, instruction=(20480, 3, 'cmp', 'esi, 0x100c')), 'esi, 0x100c')

    def test_different_array_extents_remain_different(self):
        self.db.bulk_insert(ImageId.RECOMP, [(8192, {'recomp_size': 16})])
        self.assertNotEqual(self.asm(ImageId.ORIG, 4108), self.asm(ImageId.RECOMP, 8208))

    def test_unknown_relocated_pointer_gets_no_placeholder(self):
        self.assertEqual(self.asm(ImageId.ORIG, 28672), 'esi, 0x7000')

    def test_decoded_eax_imm32_pointer(self):
        instruction = next(capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32).disasm_lite(bytes.fromhex('3d0c100000'), 20480))
        self.assertEqual(self.asm(ImageId.ORIG, 4108, reloc_at=20481, instruction=instruction), 'eax, array+12 (OFFSET)')

    def test_decoded_memory_imm32_pointer(self):
        instruction = next(capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32).disasm_lite(bytes.fromhex('813d007000000c100000'), 20480))
        self.assertEqual(self.asm(ImageId.ORIG, 4108, reloc_at=20486, instruction=instruction), 'dword ptr [<OFFSET1>], array+12 (OFFSET)')

    def test_64bit_comparison_does_not_enable_endpoint(self):
        lookup = create_name_lookup(self.db, ImageId.ORIG, lambda _: None, lambda _, off: f'+{off}')
        address = create_name_lookup(self.db, ImageId.ORIG, lambda _: None, lambda _, off: f'+{off}', address_only=True)
        parser = ParseAsm(name_lookup=lookup, address_lookup=address, is_32bit=False, pointer_reloc_test=lambda _: True)
        self.assertEqual(parser.sanitize((20480, 6, 'cmp', 'esi, 0x100c'))[1], 'esi, 0x100c')

    def test_wide_string_byte_interior_is_named(self):
        self.add('wide', 32768, 36864, 16, EntityType.WIDECHAR)
        self.assertEqual(self.asm(ImageId.ORIG, 32774), self.asm(ImageId.RECOMP, 36870))
        self.assertEqual(self.asm(ImageId.ORIG, 32774), 'esi, wide+6 (OFFSET)')

    def test_offset_entity_endpoint_is_named(self):
        self.add('field', 40960, 45056, 8, EntityType.OFFSET)
        self.assertEqual(self.asm(ImageId.ORIG, 40968), self.asm(ImageId.RECOMP, 45064))
        self.assertEqual(self.asm(ImageId.ORIG, 40968), 'esi, field+8 (OFFSET)')

    def test_unmatched_string_interior_stays_literal(self):
        self.db.bulk_insert(ImageId.ORIG, [(24576, {'name': 'unmatched', 'type': EntityType.STRING, 'orig_size': 24})])
        self.assertEqual(self.asm(ImageId.ORIG, 24588), 'esi, 0x600c')
if __name__ == '__main__':
    unittest.main(verbosity=2)
