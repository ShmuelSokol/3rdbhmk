"""Runs only actual pure-Python launch contract/path logic; no fake Unreal objects."""
import unittest
from launcher_contract import canonical, same, below, launch_inputs, check_path_readbacks

class Paths(unittest.TestCase):
    def test_normalization(self):
        self.assertTrue(same('c:\\Sessions\\Session-01\\', 'C:/Sessions/Session-01'))
        self.assertTrue(below('C:/Sessions/Session-01/User', 'C:/Sessions/Session-01'))
        self.assertFalse(below('C:/Sessions/Session-010/User', 'C:/Sessions/Session-01'))
        self.assertFalse(below('C:/Sessions/Session-01', 'C:/Sessions/Session-01'))

    def test_rejected_syntax(self):
        for path in ['relative', 'C:relative', '//server/share/x', '//?/C:/x',
                     'C:/x/../y', 'C:/x/./y', 'C:/x//y', 'C:/x:ads', 'C:/x.',
                     'C:/x ', 'C:/CON/file', 'C:/aux.ini', 'C:/LPT1/x',
                     'C:/x\x00', 'C:/x"', 'C:/x*', 'C:/', 'C:/é', 'C:/x//',
                     'C:/'+('a'*101), 'C:/x\ny']:
            with self.subTest(path=path), self.assertRaises(ValueError): canonical(path)

    def test_args(self):
        c=launch_inputs('C:/Owned Sessions/s01','settings-s01','save-s01')
        self.assertEqual(c['tokens'][0], '-UserDir=C:/Owned Sessions/s01/User')
        self.assertTrue(c['exact_suffix'].startswith('-UserDir="C:/Owned Sessions/s01/User" '))
        self.assertEqual(len(c['tokens']),5)
        self.assertEqual(len(c['precreate_directories']),5)
        self.assertTrue(all(below(p,c['root']) for p in c['precreate_directories']))
        for slot in ['../escape', 'x/y', 'x:ads', 'CON', 'x y', 'x" -UserDir=X', 'x'*65]:
            with self.subTest(slot=slot), self.assertRaises(ValueError): launch_inputs(c['root'],slot,'save')
        for slot in ['save_00','SAVE_AUTO','save_63']:
            with self.subTest(slot=slot), self.assertRaises(ValueError): launch_inputs(c['root'],slot,'save')

    def test_effective_paths_not_intent(self):
        c=launch_inputs('C:/Owned/s01','settings','save')
        r={'user':c['root']+'/User', 'saved':c['root']+'/User/Saved',
           **{k:c[k] for k in ['game_ini','game_user_settings_ini','save_directory']}}
        self.assertTrue(check_path_readbacks(c,r))
        for key in r:
            wrong=dict(r); wrong[key]=r[key].replace('/s01/','/s02/')
            self.assertFalse(check_path_readbacks(c,wrong),key)
        wrong=dict(r);wrong['game_ini']='C:/Project/Config/DefaultGame.ini'
        self.assertFalse(check_path_readbacks(c,wrong))
        wrong=dict(r);wrong['saved']+='-other'
        self.assertFalse(check_path_readbacks(c,wrong))

if __name__=='__main__': unittest.main(verbosity=2)
