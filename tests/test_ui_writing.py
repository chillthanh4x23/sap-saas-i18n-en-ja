import importlib.util
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('ui_audit',Path(__file__).resolve().parents[1]/'scripts/audit-ui-writing.py')
ui=importlib.util.module_from_spec(spec);spec.loader.exec_module(ui)


LEGACY={'uiWriting':{'style':'compact'}}


class LegacyCompactStyleTests(unittest.TestCase):
    """The original compact heuristic, kept selectable with style: compact."""
    def test_sentence_button_is_flagged_and_not_rewritten(self):
        target={'button':'新しいリクエストを作成します'}
        result=ui.audit({'button':'Create new request'},target,LEGACY)
        self.assertIn('compact-slot-sentence-ending',result['strings'][0]['findingCodes'])
        self.assertEqual(target['button'],'新しいリクエストを作成します')

    def test_requested_noun_action_ending_is_accepted_by_style_screen(self):
        result=ui.audit({'button':'Create new request'},{'button':'新リクエストを作成'},LEGACY)
        self.assertNotIn('compact-slot-sentence-ending',result['strings'][0]['findingCodes'])

    def test_negative_message_is_only_flagged_never_stripped_or_reversed(self):
        result=ui.audit({'error':'Cannot delete'},{'error':'削除できません'},LEGACY)
        self.assertEqual(result['strings'][0]['japanese'],'削除できません')
        self.assertIn('compact-message-ending',result['strings'][0]['findingCodes'])

    def test_display_cells_differ_from_raw_character_count(self):
        self.assertEqual(ui.display_cells('abcd'),4)
        self.assertEqual(ui.display_cells('あいうえ'),8)
        self.assertEqual(ui.display_cells('e\u0301'),1)

    def test_short_english_is_not_forced_to_impossible_equal_cell_budget(self):
        result=ui.audit({'go':'Go'},{'go':'実行'},LEGACY)
        self.assertNotIn('estimated-width-growth',result['strings'][0]['findingCodes'])

    def test_substantial_width_growth_is_reported(self):
        result=ui.audit({'title':'Configuration'},{'title':'アプリケーション全体の詳細な設定内容'},LEGACY)
        self.assertIn('estimated-width-growth',result['strings'][0]['findingCodes'])

    def test_placeholders_and_markup_do_not_fake_literal_width(self):
        self.assertEqual(ui.display_cells('<b>{{fileName}}</b>保存'),4)
        self.assertEqual(ui.display_cells('${id}保存'),4)

    def test_explicit_role_overrides_key_heuristic(self):
        result=ui.audit({'title':'Failed'},{'title':'失敗しました'},{'uiWriting':{'style':'compact','rolesByKey':{'/title':'message'}}})
        self.assertEqual(result['strings'][0]['roleBasis'],'profile')
        self.assertIn('compact-message-ending',result['strings'][0]['findingCodes'])

    def test_exception_binds_exact_text_and_reason(self):
        profile={'uiWriting':{'style':'compact','exceptionsByKey':{'/error':{'source':'Cannot delete','target':'削除できません','codes':['compact-message-ending'],'reason':'Retain this explicit negative statement.'}}}}
        result=ui.audit({'error':'Cannot delete'},{'error':'削除できません'},profile)
        self.assertEqual(result['counts']['unreviewedFindings'],0)
        with self.assertRaisesRegex(ValueError,'bind exact'):ui.audit({'error':'Cannot delete'},{'error':'保存できません'},profile)

    def test_audit_never_certifies_real_layout(self):
        result=ui.audit({'save':'Save'},{'save':'保存'},LEGACY)
        self.assertFalse(result['actualUILayoutChecked'])
        self.assertFalse(result['pixelWidthMeasured'])


if __name__=='__main__':unittest.main()
