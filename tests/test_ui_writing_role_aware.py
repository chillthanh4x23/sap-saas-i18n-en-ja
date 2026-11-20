import importlib.util
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('ui_audit_role',Path(__file__).resolve().parents[1]/'scripts/audit-ui-writing.py')
ui=importlib.util.module_from_spec(spec);spec.loader.exec_module(ui)


def row(source,target,profile=None,peers=None):
    return ui.audit(source,target,profile,peers)['strings'][0]


def codes(source,target,profile=None,peers=None):
    return row(source,target,profile,peers)['findingCodes']


class RoleResolutionTests(unittest.TestCase):
    def test_default_style_is_role_aware(self):
        self.assertEqual(ui.audit({'save':'Save'},{'save':'保存'})['style'],'role-aware')

    def test_profile_key_beats_pattern_beats_key_rule(self):
        profile={'uiWriting':{'rolesByKey':{'/a/messages/x':'label'},'rolesByPattern':{'/a/messages/*':'heading'}}}
        r=ui.audit({'a':{'messages':{'x':'Saved','y':'Saved'}}},{'a':{'messages':{'x':'保存済み','y':'保存済み'}}},profile)['strings']
        self.assertEqual((r[0]['role'],r[0]['roleBasis'],r[0]['roleConfidence']),('label','profile-key','high'))
        self.assertEqual((r[1]['role'],r[1]['roleBasis']),('heading','profile-pattern:/a/messages/*'))

    def test_longest_pattern_wins(self):
        profile={'uiWriting':{'rolesByPattern':{'*':'label','*/errors/*':'message'}}}
        self.assertEqual(row({'x':{'errors':{'y':'Bad input.'}}},{'x':{'errors':{'y':'入力が不正です。'}}},profile)['role'],'message')

    def test_short_text_under_message_path_is_a_label(self):
        self.assertEqual(row({'notification':{'comment':'Comment'}},{'notification':{'comment':'コメント'}})['role'],'label')

    def test_short_outcome_under_message_path_stays_a_message(self):
        self.assertEqual(row({'messages':{'deleteFailed':'Delete failed'}},{'messages':{'deleteFailed':'削除に失敗しました'}})['role'],'message')

    def test_title_under_error_path_is_a_heading(self):
        self.assertEqual(row({'error':{'title':'Something went wrong'}},{'error':{'title':'問題が発生しました'}})['role'],'heading')

    def test_single_word_named_after_ui_concept_is_a_label(self):
        self.assertEqual(row({'editor':{'placeholder':'Placeholder'}},{'editor':{'placeholder':'プレースホルダー'}})['role'],'label')

    def test_input_prompt_is_guidance(self):
        self.assertEqual(row({'input':{'placeholder':'Search by name...'}},{'input':{'placeholder':'名前で検索...'}})['role'],'guidance')

    def test_status_description_sentence_is_a_message(self):
        self.assertEqual(row({'status':{'success':{'desc':'Request created.'}}},{'status':{'success':{'desc':'リクエストを作成しました。'}}})['role'],'message')

    def test_conflicting_english_shape_lowers_confidence(self):
        r=row({'columns':{'note':'Please try again later.'}},{'columns':{'note':'後でもう一度お試しください。'}})
        self.assertEqual(r['roleConfidence'],'low')

    def test_unknown_role_profile_value_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unsupported UI role'):
            ui.audit({'a':'A'},{'a':'A'},{'uiWriting':{'rolesByPattern':{'*':'banner'}}})


class PeerEvidenceTests(unittest.TestCase):
    def duplicates(self):
        return {'crossApplicationGroups':[{'english':'Upload failed.','occurrences':[
            {'file':'a.json','application':'A','key':'/messages/upload'},
            {'file':'b.json','application':'B','key':'/toast/upload'},
            {'file':'mine.json','application':'C','key':'/x'}]}],'withinApplicationGroups':[]}

    def test_peers_supply_role_when_key_gives_none(self):
        peers=ui.PeerIndex(self.duplicates(),None,'C','mine.json')
        r=row({'x':'Upload failed.'},{'x':'アップロード失敗'},None,peers)
        self.assertEqual((r['role'],r['roleBasis'],r['roleConfidence']),('message','peer','medium'))
        self.assertIn('message-note-style',r['findingCodes'])

    def test_semantic_review_split_blocks_peer_roles(self):
        review={'groups':[{'english':'Upload failed.','semanticDisposition':'keep-separate-ui-roles'}]}
        peers=ui.PeerIndex(self.duplicates(),review,'C','mine.json')
        r=row({'x':'Upload failed.'},{'x':'アップロード失敗'},None,peers)
        self.assertNotEqual(r['roleBasis'],'peer')
        self.assertTrue(any('semantic review' in n for n in r['roleNotes']))


class ControlRuleTests(unittest.TestCase):
    def test_polite_ending_in_button_is_flagged(self):
        self.assertIn('control-sentence-ending',codes({'actions':{'save':'Save'}},{'actions':{'save':'保存します'}}))

    def test_verb_ending_button_is_flagged(self):
        self.assertIn('action-verb-ending',codes({'actions':{'save':'Save'}},{'actions':{'save':'保存する'}}))

    def test_noun_button_passes(self):
        self.assertEqual(codes({'actions':{'save':'Save'}},{'actions':{'save':'保存'}}),[])


class MessageRuleTests(unittest.TestCase):
    def test_correct_polite_message_raises_nothing(self):
        self.assertEqual(codes({'errors':{'network':'Unable to reach the server. Please check your connection.'}},
                               {'errors':{'network':'サーバーに接続できません。接続を確認してください。'}}),[])

    def test_note_style_message_is_flagged(self):
        c=codes({'errors':{'network':'Unable to reach the server. Please check your connection.'}},{'errors':{'network':'サーバーに接続不可。接続を確認'}})
        self.assertIn('message-note-style',c);self.assertIn('request-form-missing',c)

    def test_missing_request_form_is_flagged(self):
        self.assertIn('request-form-missing',codes({'errors':{'x':'Extraction failed. Try again.'}},{'errors':{'x':'抽出に失敗しました。再試行します。'}}))

    def test_shite_kudasai_is_not_wordy(self):
        r=ui.audit({'errors':{'x':'Please fix form errors.'}},{'errors':{'x':'フォームのエラーを修正してください。'}})
        self.assertEqual(r['counts']['findings'],0)

    def test_stiff_phrasing_is_info_only(self):
        r=ui.audit({'errors':{'x':'Please contact support.'}},{'errors':{'x':'サポートにご連絡をお願いいたします。'}})
        self.assertEqual(r['counts']['unreviewedFindings'],0)
        self.assertEqual(r['findings'][0]['code'],'formal-phrasing')

    def test_two_word_status_is_not_treated_as_sentence(self):
        self.assertEqual(codes({'validation':{'state':'Validation Failed'}},{'validation':{'state':'検証失敗'}}),[])

    def test_clipped_hint_is_valid(self):
        r=ui.audit({'help':{'tip':'Start by adding fields to define your data.'}},{'help':{'tip':'フィールドを追加してデータを定義'}})
        self.assertEqual(r['counts']['findings'],0)

    def test_clipped_instruction_hint_needs_no_request_form(self):
        r=ui.audit({'help':{'tip':'Select a tool to configure it.'}},{'help':{'tip':'ツールを選択して設定'}})
        self.assertEqual(r['counts']['findings'],0)

    def test_clipped_empty_state_text_is_valid(self):
        r=ui.audit({'list':{'noRules':'No validation rules configured. Use the buttons above to add rules.'}},{'list':{'noRules':'検証ルール未設定。上のボタンでルール追加'}})
        self.assertEqual(r['counts']['findings'],0)

    def test_instruction_in_empty_area_is_empty_state_text(self):
        r=row({'search':{'empty':{'desc':'Enter a material number above or ask the assistant.'}}},{'search':{'empty':{'desc':'上に品目番号を入力、またはアシスタントに質問'}}})
        self.assertEqual((r['role'],r['findingCodes']),('empty-state',[]))

    def test_statement_in_empty_area_is_a_message(self):
        self.assertEqual(row({'duplicates':{'none':{'desc':'Your material appears to be unique.'}}},{'duplicates':{'none':{'desc':'一意と推定'}}})['role'],'message')

    def test_polite_heading_in_result_context_is_flagged(self):
        for key in ('success','error','none','empty'):
            with self.subTest(key=key):
                self.assertIn('control-sentence-ending',codes({key:{'title':'Done'}},{key:{'title':'完了しました'}}))


class WidthTests(unittest.TestCase):
    def test_standard_loanword_within_floor_passes(self):
        self.assertEqual(codes({'actions':{'cancel':'Cancel'}},{'actions':{'cancel':'キャンセル'}}),[])

    def test_long_label_is_flagged(self):
        self.assertIn('estimated-width-growth',codes({'columns':{'cfg':'Configuration'}},{'columns':{'cfg':'アプリケーション全体の詳細な設定内容'}}))

    def test_standard_term_is_exempt(self):
        profile={'uiWriting':{'standardTerms':['アプリケーション全体の詳細な設定内容']}}
        self.assertNotIn('estimated-width-growth',codes({'columns':{'cfg':'Configuration'}},{'columns':{'cfg':'アプリケーション全体の詳細な設定内容'}},profile))

    def test_messages_are_not_width_checked(self):
        self.assertNotIn('estimated-width-growth',codes({'errors':{'x':'Failed.'}},{'errors':{'x':'処理中に予期しないエラーが発生しました。'}}))

    def test_width_budget_is_configurable(self):
        profile={'uiWriting':{'widthBudget':{'minimumCells':4,'growthRatio':1.0}}}
        self.assertIn('estimated-width-growth',codes({'actions':{'cancel':'Cancel'}},{'actions':{'cancel':'キャンセル'}},profile))


class HeldOutFixTests(unittest.TestCase):
    """Synthetic regression cases for role and width inference."""
    def test_short_outcome_notice_is_a_message_with_polite_japanese_accepted(self):
        r=row({'approval':{'actions':{'reminderSent':'Reminder sent'}}},{'approval':{'actions':{'reminderSent':'リマインダーを送信しました'}}})
        self.assertEqual((r['role'],r['findingCodes']),('message',[]))

    def test_count_outcome_notice_is_a_message(self):
        self.assertEqual(row({'data':{'updated_one':'{{count}} updated'}},{'data':{'updated_one':'{{count}} 件更新しました'}})['role'],'message')

    def test_result_words_in_a_column_stay_a_label(self):
        self.assertEqual(row({'columns':{'found':'Records Found'}},{'columns':{'found':'検出レコード'}})['role'],'label')

    def test_polite_yes_no_question_is_accepted(self):
        self.assertEqual(codes({'dialog':{'confirmDelete':'Delete all records?'}},{'dialog':{'confirmDelete':'すべてのレコードを削除しますか？'}}),[])

    def test_input_prompt_with_required_marker_is_guidance(self):
        self.assertEqual(row({'workflow':{'rejectionReasonRequired':'Rejection reason (required)...'}},{'workflow':{'rejectionReasonRequired':'却下理由（必須）...'}})['role'],'guidance')

    def test_small_width_overflow_is_info_only(self):
        r=ui.audit({'actions':{'add':'Add Spacer'}},{'actions':{'add':'スペーサーを追加'}})
        self.assertEqual(r['counts']['unreviewedFindings'],0)
        self.assertEqual(r['findings'][0]['code'],'estimated-width-growth')


class PolicyAlignmentTests(unittest.TestCase):
    def test_short_confirmation_question_is_allowed(self):
        self.assertEqual(codes({'dialog':{'confirmDelete':'Are you sure you want to delete the selected items?'}},{'dialog':{'confirmDelete':'選択項目を削除？'}}),[])

    def test_confirmation_without_question_or_polite_ending_is_flagged(self):
        self.assertIn('message-note-style',codes({'dialog':{'confirmDelete':'Are you sure you want to delete the selected items?'}},{'dialog':{'confirmDelete':'選択項目を削除'}}))


class BugFixTests(unittest.TestCase):
    def test_english_fallback_is_not_style_checked(self):
        r=ui.audit({'errors':{'x':'Failed To Save'}},{'errors':{'x':'Failed To Save'}})
        self.assertEqual((r['counts']['findings'],r['counts']['skippedWithoutJapaneseText']),(0,1))

    def test_trailing_placeholder_does_not_hide_polite_ending(self):
        self.assertEqual(codes({'errors':{'x':'Please fill in the required fields: {{fields}}'}},{'errors':{'x':'必須フィールドを入力してください: {{fields}}'}}),[])


class AbbreviationAndAccessibilityTests(unittest.TestCase):
    def test_abbreviation_full_stop_is_not_a_sentence(self):
        self.assertEqual(row({'grid':{'sapInvoiceNumber':'SAP Invoice No.'}},{'grid':{'sapInvoiceNumber':'SAP請求書番号'}})['role'],'label')

    def test_variant_is_not_an_aria_key(self):
        self.assertNotEqual(row({'grid':{'variantName':'Variant Name'}},{'grid':{'variantName':'バリアント名'}})['role'],'accessibility')

    def test_aria_keys_are_still_accessibility(self):
        for key in ('ariaLabel','closeAriaLabel','srOnlyText'):
            with self.subTest(key=key):
                self.assertEqual(row({'x':{key:'Close dialog'}},{'x':{key:'ダイアログを閉じる'}})['role'],'accessibility')


class SafetyTests(unittest.TestCase):
    def test_provisional_role_is_low_confidence_and_source_bound(self):
        profile={'uiWriting':{'provisionalRolesByKey':{'/viewSaved':{'role':'message','source':'View saved','reason':'Completed operation notice.','status':'provisional'}}}}
        result=row({'viewSaved':'View saved'},{'viewSaved':'ビューを保存しました。'},profile)
        self.assertEqual((result['role'],result['roleBasis'],result['roleConfidence']),('message','profile-provisional','low'))
        with self.assertRaisesRegex(ValueError,'source changed'):
            ui.audit({'viewSaved':'View saved again'},{'viewSaved':'保存しました。'},profile)

    def test_confirmed_role_beats_provisional_choice(self):
        profile={'uiWriting':{'rolesByKey':{'/x':'status'},'provisionalRolesByKey':{'/x':{'role':'message','source':'Saved','reason':'Temporary.','status':'provisional'}}}}
        self.assertEqual(row({'x':'Saved'},{'x':'保存済み'},profile)['roleConfidence'],'high')

    def test_invalid_provisional_role_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Provisional role'):
            ui.audit({'x':'Saved'},{'x':'保存済み'},{'uiWriting':{'provisionalRolesByKey':{'/x':{'role':'message'}}}})

    def test_removed_provisional_source_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'source changed'):
            ui.audit({}, {}, {'uiWriting':{'provisionalRolesByKey':{'/x':{'role':'message','source':'Saved','reason':'Temporary.','status':'provisional'}}}})

    def test_exception_must_bind_exact_text(self):
        profile={'uiWriting':{'exceptionsByKey':{'/columns/cfg':{'source':'Configuration','target':'別の訳','codes':['estimated-width-growth'],'reason':'x'}}}}
        with self.assertRaisesRegex(ValueError,'bind exact'):
            ui.audit({'columns':{'cfg':'Configuration'}},{'columns':{'cfg':'アプリケーション全体の詳細な設定内容'}},profile)

    def test_inputs_are_not_modified_and_layout_not_certified(self):
        target={'errors':{'x':'サーバーに接続不可'}}
        r=ui.audit({'errors':{'x':'Unable to reach the server.'}},target)
        self.assertEqual(target,{'errors':{'x':'サーバーに接続不可'}})
        self.assertFalse(r['actualUILayoutChecked'])

    def test_low_confidence_findings_are_listed_first(self):
        r=ui.audit({'columns':{'note':'Please try again later.'},'errors':{'x':'Unable to load.'}},{'columns':{'note':'後で再試行'},'errors':{'x':'読み込み不可'}})
        self.assertEqual([f['roleConfidence'] for f in r['findings']][:1],['low'])
        self.assertIn('medium',[f['roleConfidence'] for f in r['findings']])


if __name__=='__main__':unittest.main()
