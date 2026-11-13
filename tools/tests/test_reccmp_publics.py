import unittest
from reccmp.cvdump.analysis import CvdumpAnalysis
from reccmp.cvdump.parser import CvdumpParser, PublicsEntry, GdataEntry
from reccmp.cvdump.symbols import SymbolsEntry
from reccmp.cvdump.types import CvdumpTypeKey
from reccmp.types import EntityType

class AnonymousPublicFallback(unittest.TestCase):

    def analyze(self, symbol, flags=2, proc=None, gdata=None):
        p = CvdumpParser()
        p.publics.append(PublicsEntry('S_PUB32', 1, 32, flags, symbol))
        if proc is not None:
            p.symbols.append(SymbolsEntry('S_GPROC32', 1, 32, 22, CvdumpTypeKey(4096), proc))
        if gdata is not None:
            p.globals.append(GdataEntry(1, 32, CvdumpTypeKey(34), gdata, True))
        return CvdumpAnalysis(p).nodes[0]

    def test_source_path_hashes_have_same_real_signature(self):
        a = self.analyze('?init_tss_data@?A0x06c9e004@@YAXXZ')
        b = self.analyze('?init_tss_data@?A0x3985ee41@@YAXXZ')
        self.assertEqual(a.name(), "void __cdecl `anonymous namespace'::init_tss_data(void)")
        self.assertEqual(a.name(), b.name())
        self.assertNotEqual(a.decorated_name, b.decorated_name)

    def test_data_signature_preserves_actual_type(self):
        n = self.analyze('?tss_data_native_key@?A0x3985ee41@@3KA', flags=0)
        self.assertEqual(n.name(), "unsigned long `anonymous namespace'::tss_data_native_key")
        self.assertIsNone(n.data_type)
        self.assertIsNone(n.node_type)

    def test_proc_name_takes_precedence(self):
        n = self.analyze('?init_tss_data@?A0x3985ee41@@YAXXZ', proc="`anonymous namespace'::init_tss_data")
        self.assertEqual(n.name(), "`anonymous namespace'::init_tss_data")
        self.assertEqual(n.node_type, EntityType.FUNCTION)
        self.assertEqual(n.size(), 22)

    def test_global_name_takes_precedence(self):
        n = self.analyze('?tss_data_native_key@?A0x3985ee41@@3KA', flags=0, gdata='tss_data_native_key')
        self.assertEqual(n.name(), 'tss_data_native_key')
        self.assertEqual(n.node_type, EntityType.DATA)

    def test_other_publics_unchanged(self):
        sym = '?cleanup@tss@detail@boost@@QAEXPAX@Z'
        self.assertEqual(self.analyze(sym).name(), sym)

    def test_undecodable_anonymous_name_stays_raw(self):
        sym = '?bad@?A0x1234@@invalid'
        self.assertEqual(self.analyze(sym).name(), sym)
if __name__ == '__main__':
    unittest.main()
