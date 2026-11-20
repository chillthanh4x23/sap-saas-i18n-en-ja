#!/usr/bin/env python3
"""Read-only JSON UI-style/estimated-width triage. Never rewrites Japanese or certifies rendering.

Two styles:
- role-aware (default): compact controls, natural polite message bodies; roles resolved from the
  profile, built-in key rules, optional peer evidence and English shape, each with a confidence.
- compact (legacy): the original heuristic, kept so earlier run results can be reproduced.
"""
from __future__ import annotations
import argparse
import fnmatch
import html
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------- shared helpers

TOKENS=re.compile(r'\{\{[^{}]*\}\}|\$\{[^{}]*\}|\{[\w.-]+\}|%\d*\$?[sdif]')
TAGS=re.compile(r'</?(?:[A-Za-z][\w:.-]*|\d+)(?:\s[^<>]*?)?/?>')
TECHNICAL_TEXTS={'px','TODAY','SAP','API','CSV','JSON','XML','URL','ID','OK'}


def load(path):
    def unique(pairs):
        result={}
        for k,v in pairs:
            if k in result:raise ValueError('Duplicate JSON key: '+k)
            result[k]=v
        return result
    def reject(value):raise ValueError('Non-JSON constant: '+value)
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),object_pairs_hook=unique,parse_constant=reject)


def strings(value,parts=()):
    if isinstance(value,str):yield '/'+ '/'.join(str(p).replace('~','~0').replace('/','~1') for p in parts),value
    elif isinstance(value,dict):
        for k,v in value.items():yield from strings(v,(*parts,k))
    elif isinstance(value,list):
        for k,v in enumerate(value):yield from strings(v,(*parts,k))


def display_cells(text):
    visible=html.unescape(TAGS.sub('',TOKENS.sub('',text))).replace('`','')
    def line_width(line):
        return sum(0 if unicodedata.combining(c) or unicodedata.category(c) in {'Cf','Cc'} else 2 if unicodedata.east_asian_width(c) in {'W','F'} else 1 for c in line)
    return max((line_width(line) for line in visible.splitlines()),default=0)


# ---------------------------------------------------------------- legacy compact audit (unchanged behaviour)

LEGACY_ROLES={'action','label','status','guidance','message','confirmation','accessibility','technical','unknown'}
LEGACY_COMPACT={'action','label','status'}
POLITE=re.compile(r'(?:ください|下さい|お願いします|です|ます|でした|ました|ません|ましょう)[。.!！?？…\s]*$')
WORDY=re.compile(r'ことができます|することが|する必要があります|してください|お願いいたします|くださいませ')
LEGACY_DEFAULTS={'style':'compact','preferNounOrActionEnding':True,'estimatedWidthGrowthRatio':1.25,'minimumEstimatedWidthBudget':8,'rolesByKey':{},'exceptionsByKey':{}}
ACTION_VERBS=r'Add|Apply|Approve|Attach|Back|Cancel|Clear|Close|Confirm|Continue|Copy|Create|Delete|Discard|Download|Duplicate|Edit|Export|Generate|Hide|Import|Load|Move|Next|Open|Preview|Previous|Proceed|Publish|Reassign|Refresh|Reject|Reload|Remove|Rename|Reset|Restore|Retry|Reuse|Run|Save|Search|Select|Send|Show|Start|Stop|Submit|Test|Update|Upload|Validate|Verify|View'


def legacy_infer_role(key,english,overrides):
    if key in overrides:
        if overrides[key] not in LEGACY_ROLES:raise ValueError('Unsupported explicit UI role at '+key)
        return overrides[key],'profile'
    path=key.lower();leaf=path.rsplit('/',1)[-1]
    if re.search(r'aria|accessib',leaf):return 'accessibility','inferred'
    if english.lstrip().startswith(('{ "','{"','["')) or english in TECHNICAL_TEXTS:return 'technical','inferred'
    if 'confirm' in leaf and ('?' in english or 'cannot be undone' in english):return 'confirmation','inferred'
    if re.search(r'placeholder|tooltip|hint|desc|help',leaf):return 'guidance','inferred'
    if re.search(r'/error/|/messages/|/message/',path) or re.search(r'error|failed|success|defaultmsg',leaf):return 'message','inferred'
    if re.search(r'title|subtitle|header|label|heading',leaf):return 'label','inferred'
    if re.search(r'/status/|/badge/|/stream/',path):return 'status','inferred'
    if re.search(r'/action/|/actions/|button',path):return 'action','inferred'
    if re.match(r'^(?:Add|Apply|Approve|Attach|Back|Cancel|Clear|Close|Copy|Create|Delete|Download|Edit|Export|Generate|Hide|Import|Move|Open|Proceed|Reassign|Refresh|Reject|Reload|Remove|Restore|Retry|Reuse|Save|Search|Select|Send|Show|Start|Submit|Update|Upload|Verify|View)\b',english) and len(english)<=55:
        return 'action','inferred'
    if len(english)<=45 and len(english.split())<=5 and not re.search(r'[.!?]',english):return 'label','inferred'
    if len(english)>45:return 'guidance','inferred'
    return 'unknown','inferred'


infer_role=legacy_infer_role  # backwards-compatible name used by earlier analyses


def legacy_settings(configured):
    result={**LEGACY_DEFAULTS,**configured}
    ratio=result['estimatedWidthGrowthRatio'];minimum=result['minimumEstimatedWidthBudget']
    if isinstance(ratio,bool) or not isinstance(ratio,(int,float)) or not math.isfinite(ratio) or ratio<=0:raise ValueError('Invalid estimated-width growth ratio')
    if isinstance(minimum,bool) or not isinstance(minimum,int) or minimum<0:raise ValueError('Invalid short-source display budget')
    if result['preferNounOrActionEnding'] is not True:raise ValueError('Compact UI audit requires noun/action endings for compact slots')
    if not isinstance(result['rolesByKey'],dict) or not isinstance(result['exceptionsByKey'],dict):raise ValueError('UI roles/exceptions must be objects')
    return result


def check_exception(exception,english,japanese,key):
    if exception and (exception.get('source')!=english or exception.get('target')!=japanese or not exception.get('reason') or not isinstance(exception.get('codes'),list)):
        raise ValueError('UI exception must bind exact source/target, codes and a reason: '+key)
    return set(exception['codes']) if exception else set()


def legacy_audit(source,target,configured):
    policy=legacy_settings(configured)
    en=dict(strings(source));ja=dict(strings(target));rows=[];findings=[];role_counts=Counter()
    for key,english in en.items():
        if key not in ja:continue
        japanese=ja[key]
        role,basis=legacy_infer_role(key,english,policy['rolesByKey']);role_counts[role]+=1
        en_width,ja_width=display_cells(english),display_cells(japanese)
        budget=max(policy['minimumEstimatedWidthBudget'],math.ceil(en_width*policy['estimatedWidthGrowthRatio']))
        codes=[]
        if role!='technical':
            if POLITE.search(japanese):codes.append('compact-slot-sentence-ending' if role in LEGACY_COMPACT else 'compact-message-ending')
            if WORDY.search(japanese):codes.append('wordy-ui-framing')
            if role!='accessibility' and en_width>0 and ja_width>budget:codes.append('estimated-width-growth')
        exception=policy['exceptionsByKey'].get(key)
        retained=check_exception(exception,english,japanese,key)
        for code in codes:
            findings.append({'key':key,'code':code,'role':role,'roleBasis':basis,
                 'status':'retained-with-specific-reason' if code in retained else 'needs-review',
                 'reason':exception['reason'] if code in retained else None,
                 'sourceLiteralCells':en_width,'targetLiteralCells':ja_width,'estimatedBudgetCells':budget})
        rows.append({'key':key,'english':english,'japanese':japanese,'role':role,'roleBasis':basis,
                     'sourceLiteralCells':en_width,'targetLiteralCells':ja_width,'estimatedBudgetCells':budget,'findingCodes':codes})
    unresolved=[f for f in findings if f['status']=='needs-review']
    missing=sorted(set(en)-set(ja));extra=sorted(set(ja)-set(en))
    return {'status':'incomplete-input-pair' if missing or extra else 'needs-ui-writing-review' if unresolved else 'no-unreviewed-heuristic-findings',
       'policy':policy,'counts':{'sourceStrings':len(en),'targetStrings':len(ja),'comparedStrings':len(rows),'missingTargetStrings':len(missing),
          'extraTargetStrings':len(extra),'findings':len(findings),'unreviewedFindings':len(unresolved),'flaggedKeys':len({f['key'] for f in findings}),
          'sentenceEndingKeys':len({f['key'] for f in findings if f['code'] in {'compact-slot-sentence-ending','compact-message-ending'}}),
          'widthGrowthKeys':len({f['key'] for f in findings if f['code']=='estimated-width-growth'})},'roleCounts':dict(role_counts),
       'actualUILayoutChecked':False,'pixelWidthMeasured':False,'runtimeVariableWidthMeasured':False,
       'limitations':['Roles are inferred unless supplied by exact-key profile overrides.','Display cells are a literal-text heuristic, not actual font or component width.','Placeholders/markup and their runtime rendering are not measured.','No structural, business-meaning or native-speaker approval is provided.','The audit never edits or automatically shortens Japanese.'],
       'missingTargetKeys':missing,'extraTargetKeys':extra,'findings':findings,'strings':rows}


# ---------------------------------------------------------------- role-aware audit

ROLES={'action','label','heading','status','message','guidance','confirmation','empty-state','accessibility','technical','unknown'}
COMPACT={'action','label','heading','status'}
SENTENCE={'message','guidance','confirmation','empty-state'}
CONFIDENCE_ORDER={'low':0,'medium':1,'high':2}
ROLE_AWARE_DEFAULTS={'style':'role-aware','rolesByKey':{},'rolesByPattern':{},'provisionalRolesByKey':{},
    'widthBudget':{'minimumCells':12,'growthRatio':1.5,'toleranceCells':2,'roles':['action','label','heading','status']},
    'standardTerms':[],'exceptionsByKey':{}}
BLOCKED_PEER_DISPOSITIONS={'keep-separate-meanings','keep-separate-ui-roles'}

# Japanese ending patterns
JA_POLITE_END=re.compile(r'(?:ます|ますか|ました|ません|ませんか|ましょう|です|でした|ですか|ください|下さい|お願いします|お願いいたします)[。．.!！?？…\s]*$')
JA_CONTROL_SENTENCE_END=JA_POLITE_END
JA_ACTION_VERB_END=re.compile(r'(?:する|します|しよう)[。．.!！]*$')
JA_REQUEST=re.compile(r'ください|下さい|お願いします|お願いいたします|ませんか')
JA_FORMAL=re.compile(r'お願いいたします|くださいませ|することができます|させていただ|する必要があります')
JA_FULLSTOP=re.compile(r'[。．！？!?]$')

# English shape
EN_TECHNICAL_START=('{ "','{"','["')
EN_SENTENCE_WORDS=re.compile(r"\b(?:is|are|was|were|has|have|had|been|not|no longer|unable|cannot|can't|could|couldn't|failed|successfully|required|unavailable|please|try|already|appears|will|would|must|should|occurred|encountered|went wrong)\b",re.I)
EN_REQUEST=re.compile(r"(?:^|[.!?]\s+)(?:Please\b|Try again\b|Try\b|Check\b|Fix\b|Enter\b|Select\b|Fill in\b|Contact\b|Refresh\b|Reload\b|Make sure\b|Ensure\b|Wait\b)")
EN_ACTION_START=re.compile(r'^(?:'+ACTION_VERBS+r')\b')
EN_INPUT_PROMPT=re.compile(r'(?:\.\.\.|…)\s*$|^e\.g\.',re.I)
EN_PAST_OUTCOME=re.compile(r"(?:^|\s)(?:\w+ed|sent|found|done|made|begun|run|set|built|lost|chosen|taken|written|shown|hidden|started|stopped|missing|in progress)[!.]?$",re.I)
EN_OUTCOME=re.compile(r'\b(?:failed|failure|error|errors|successful|successfully|succeeded|complete|completed|saved|deleted|created|updated|copied|unavailable|not found|expired|denied)\b',re.I)


ABBREVIATION_END=re.compile(r'\b(?:No|Nr|Qty|Ref|Inc|Ltd|Co|vs|approx|etc)\.$',re.I)


def english_is_sentence(english):
    text=english.strip()
    if not text:return False
    if ABBREVIATION_END.search(text) and len(text.split())<=4:return False  # "SAP Invoice No." is a label
    if re.search(r'[.!?]$',text) and not EN_INPUT_PROMPT.search(text):return True
    if text.lower().startswith('please '):return True
    words=len(text.split())
    if words>=6:return True
    # One- or two-word texts such as "Required" or "Validation Failed" are labels/statuses, not sentences.
    return words>=3 and bool(EN_SENTENCE_WORDS.search(text))


def is_outcome_notice(english):
    """Short result notice such as "Reminder sent", "{{count}} updated", "View saved"."""
    text=TOKENS.sub('X',english.strip())
    words=len(text.split())
    if words<2 or words>7 or EN_ACTION_START.match(text) or text.endswith('?'):return False
    return bool(EN_PAST_OUTCOME.search(text) or re.search(r'\b(?:successfully|failed|complete|completed)\b',text,re.I))


def english_role(english):
    """Role from English shape alone (low confidence)."""
    text=english.strip()
    if text.startswith(EN_TECHNICAL_START) or text in TECHNICAL_TEXTS:return 'technical'
    if text.endswith('?'):return 'confirmation'
    if EN_INPUT_PROMPT.search(text):return 'guidance'
    if is_outcome_notice(text):return 'message'
    words=len(text.split())
    if EN_ACTION_START.match(text) and words<=4 and not re.search(r'[.!?]$',text):return 'action'
    if english_is_sentence(text):
        return 'message' if re.search(r'error|fail|unable|cannot|could not|success|went wrong|please try|unavailable|not found|required|invalid|denied',text,re.I) else 'guidance'
    if words<=5:return 'label'
    return 'unknown'


def family(role):
    return 'compact' if role in COMPACT else 'sentence' if role in SENTENCE else role


def segments(key):
    return [s for s in key.lower().split('/') if s]


def key_rule_role(key,english):
    """Built-in key rules (medium confidence). Returns role or None."""
    role=_key_rule_role(key,english)
    text=english.strip();parts=set(segments(key)[:-1])
    if role in COMPACT|{'message','empty-state'} and EN_INPUT_PROMPT.search(text) and role!='heading':return 'guidance'
    if role in COMPACT and role!='heading':
        # Column/field/filter/status containers hold labels even when worded like results ("Records Found").
        container=bool(parts & {'columns','column','fields','labels','filters','tabs','headers','status','statuses','badge','badges','statusbadge','states'})
        if re.search(r'[.!?]$',text) and english_is_sentence(text) or text.lower().startswith('please '):return english_role(text)
        if is_outcome_notice(text) and not container:return 'message'
    return role


def _key_rule_role(key,english):
    parts=segments(key)
    if not parts:return None
    leaf=parts[-1];parents=set(parts[:-1]);text=english.strip();words=len(text.split())
    single_word=words==1 and not re.search(r'[.!?…]',text)
    # Short texts without sentence punctuation are controls unless they state an outcome ("Delete failed").
    short=words<=3 and not re.search(r'[.!?…]',text) and not english_is_sentence(text)
    outcome=bool(EN_OUTCOME.search(text))
    verb_start=bool(EN_ACTION_START.match(text)) and words<=4 and not re.search(r'[.!?]$',text) and not outcome
    raw_leaf=key.rsplit('/',1)[-1]
    # "aria" only as its own word: ariaLabel, aria_label, srOnly - not "variant".
    if re.match(r'aria(?:[A-Z_-]|$)',raw_leaf) or re.search(r'[a-z]Aria[A-Z]|accessib|screenreader|sronly',raw_leaf,re.I if False else 0) or re.search(r'accessib|screenreader|sronly',leaf):return 'accessibility'
    if text.startswith(EN_TECHNICAL_START) or text in TECHNICAL_TEXTS:return 'technical'
    # A key literally named after a UI concept, holding that word, is a field label (e.g. "Placeholder").
    if single_word and leaf in {'placeholder','tooltip','hint','message','error','description','status','title','label'}:return 'label'
    if 'confirm' in leaf:
        if text.endswith('?') or re.search(r'cannot be undone|are you sure',text,re.I):return 'confirmation'
        if re.search(r'title|header|heading',leaf):return 'heading'
    if 'placeholder' in leaf or leaf=='placeholder' or 'placeholder' in parents:return 'guidance'
    if re.fullmatch(r'(?:none|empty|nodata|noresults?|noitems?|no[a-z]+found|emptystate)',leaf) or re.match(r'^no[A-Z]',key.rsplit('/',1)[-1]) or 'emptystate' in leaf:
        return 'empty-state'
    if 'empty' in parents or 'emptystate' in parents or 'none' in parents:
        if re.search(r'title|header|heading',leaf) and not english_is_sentence(text):return 'heading'
        # A statement ("Your material appears to be unique.") is a result message; an instruction is empty-state text.
        if re.fullmatch(r'(?:desc|description|text|body|msg|message)',leaf) and re.search(r'[.!]$',text) and not (EN_REQUEST.search(text) or EN_ACTION_START.match(text)):return 'message'
        return 'empty-state'
    result_parents=parents & {'success','failed','failure','error','errors','pending','result','toast','toasts','notification','notifications','alert','alerts','messages'}
    if re.fullmatch(r'(?:desc|description|subtitle|detail|details|text|body|msg|defaultmsg|content)',leaf) and result_parents:return 'message'
    if parents & {'error','errors','message','messages','toast','toasts','notification','notifications','alerts'}:
        if re.search(r'title|header|heading',leaf) and not re.search(r'[.!]$',text):return 'heading'
        if verb_start:return 'action'
        if short and (single_word or not outcome):return 'label'
        return 'message'
    if result_parents and english_is_sentence(text) and not re.search(r'title$|header$|heading$',leaf):return 'message'
    if re.search(r'(?:error|failed|failure|success|msg|unavailable|required|exists|invalid|notfound)$',leaf) and not single_word:
        if english_is_sentence(text) or (re.search(r'msg$|error$|failed$|success$',leaf) and outcome):return 'message'
    if re.search(r'tooltip|hint|helptext|help$|desc$|description$|subtitle$|info$|instructions?',leaf):
        return 'label' if short else 'guidance'
    if re.search(r'title$|header$|heading$',leaf) or leaf in {'title','header','heading'}:return 'heading'
    if parents & {'action','actions','buttons','button','btn','menu'} or re.search(r'(?:button|btn)$',leaf):
        return 'action' if verb_start or text in {'OK','Back','Next','Cancel','Close','Done'} else 'label'
    if parents & {'status','statuses','badge','badges','statusbadge','states','stream'} or leaf.startswith('status'):
        return 'action' if verb_start else 'status'
    if parents & {'columns','column','fields','labels','filters','tabs','headers'} or re.search(r'label$',leaf):return 'label'
    return None


def pattern_role(key,patterns):
    matches=[(len(p),p,r) for p,r in patterns.items() if fnmatch.fnmatchcase(key,p)]
    if not matches:return None,None
    matches.sort(reverse=True)
    return matches[0][2],matches[0][1]


def role_aware_settings(configured):
    result={**ROLE_AWARE_DEFAULTS,**configured}
    width={**ROLE_AWARE_DEFAULTS['widthBudget'],**(configured.get('widthBudget') or {})}
    ratio=width['growthRatio'];minimum=width['minimumCells'];tolerance=width['toleranceCells']
    if isinstance(tolerance,bool) or not isinstance(tolerance,int) or tolerance<0:raise ValueError('Invalid width tolerance')
    if isinstance(ratio,bool) or not isinstance(ratio,(int,float)) or not math.isfinite(ratio) or ratio<=0:raise ValueError('Invalid estimated-width growth ratio')
    if isinstance(minimum,bool) or not isinstance(minimum,int) or minimum<0:raise ValueError('Invalid minimum width budget')
    if not set(width['roles'])<=ROLES:raise ValueError('Unsupported role in widthBudget.roles')
    result['widthBudget']=width
    for name in ('rolesByKey','rolesByPattern','provisionalRolesByKey','exceptionsByKey'):
        if not isinstance(result[name],dict):raise ValueError(name+' must be an object')
    for key,decision in result['provisionalRolesByKey'].items():
        if not isinstance(decision,dict) or decision.get('role') not in ROLES or not isinstance(decision.get('source'),str) or not decision.get('reason') or decision.get('status')!='provisional':
            raise ValueError('Provisional role needs role, exact source, reason and status=provisional: '+key)
    for where,mapping in (('rolesByKey',result['rolesByKey']),('rolesByPattern',result['rolesByPattern'])):
        bad=[k for k,v in mapping.items() if v not in ROLES]
        if bad:raise ValueError(f'Unsupported UI role in {where}: '+bad[0])
    if not isinstance(result['standardTerms'],list):raise ValueError('standardTerms must be a list')
    return result


class PeerIndex:
    """Same-English occurrences from an optional duplicate report, excluding semantic-review splits."""
    def __init__(self,duplicates=None,semantic_review=None,application=None,source_file=None):
        self.by_english={};self.blocked=set();self.application=application;self.source_file=source_file
        if semantic_review:
            self.blocked={g['english'] for g in semantic_review.get('groups',[]) if g.get('semanticDisposition') in BLOCKED_PEER_DISPOSITIONS}
        if duplicates:
            for group in duplicates.get('crossApplicationGroups',[])+duplicates.get('withinApplicationGroups',[]):
                self.by_english[group['english']]=group['occurrences']

    def evidence(self,key,english):
        if english in self.blocked:return {'status':'blocked-by-semantic-review','roles':{}}
        occurrences=self.by_english.get(english)
        if not occurrences:return None
        roles=Counter();examples=[]
        for o in occurrences:
            if o['key']==key and (self.source_file is None or o['file']==self.source_file):continue
            role=key_rule_role(o['key'],english)
            if role is None:continue
            roles[role]+=1
            if len(examples)<3:examples.append({'application':o['application'],'key':o['key'],'role':role})
        if not roles:return None
        families=Counter()
        for r,n in roles.items():families[family(r)]+=n
        return {'status':'available','roles':dict(roles),'families':dict(families),'examples':examples}


def resolve_role(key,english,policy,peers):
    """Return (role, basis, confidence, notes)."""
    notes=[]
    english_guess=english_role(english)
    if key in policy['rolesByKey']:return policy['rolesByKey'][key],'profile-key','high',notes
    provisional=policy['provisionalRolesByKey'].get(key)
    if provisional:
        if provisional['source']!=english:raise ValueError('Provisional role source changed: '+key)
        return provisional['role'],'profile-provisional','low',['Provisional AI decision; user confirmation pending. '+provisional['reason']]
    role,pattern=pattern_role(key,policy['rolesByPattern'])
    if role:return role,'profile-pattern:'+pattern,'high',notes
    peer=peers.evidence(key,english) if peers else None
    keyed=key_rule_role(key,english)
    if keyed:
        confidence='medium'
        raw=_key_rule_role(key,english)
        if raw and family(raw)!=family(keyed) and family(raw) in {'compact','sentence'}:
            confidence='low';notes.append(f'key name suggests {raw}; English shape overrides')
        if english_guess not in {'unknown','technical'} and family(english_guess)!=family(keyed) and family(keyed) in {'compact','sentence'} and family(english_guess) in {'compact','sentence'}:
            confidence='low';notes.append(f'English shape suggests {english_guess}')
        if peer and peer['status']=='available':
            other={f for f in peer['families'] if f!=family(keyed) and f in {'compact','sentence'}}
            if other:confidence='low';notes.append('same English elsewhere resolves to '+'/'.join(sorted(other)))
        return keyed,'key-rule',confidence,notes
    if peer and peer['status']=='available':
        top_role,top_n=Counter(peer['roles']).most_common(1)[0]
        fam=family(top_role);agree=peer['families'].get(fam,0);total=sum(peer['families'].values())
        if agree==total:
            confidence='medium' if total>=2 else 'low'
            if english_guess not in {'unknown','technical'} and family(english_guess)!=fam:confidence='low';notes.append(f'English shape suggests {english_guess}')
            return top_role,'peer',confidence,notes+[f"{total} same-English key(s) elsewhere"]
        notes.append('same-English keys elsewhere disagree')
    if peer and peer['status']=='blocked-by-semantic-review':notes.append('peer roles not used: semantic review marks this English as separate meanings/roles')
    text=english.strip()
    confidence='medium' if english_guess=='label' and len(text.split())<=3 and not re.search(r'[.!?…]',text) else 'low'
    return english_guess,'english',confidence,notes


JA_TEXT=re.compile(r'[\u3040-\u30ff\u3400-\u9fff]')
TRAILING_TOKENS=re.compile(r'(?:\s*[:：]?\s*(?:\{\{[^{}]*\}\}|\$\{[^{}]*\}|\{[\w.-]+\}|%\d*\$?[sdif]))+\s*$')


def ending(japanese):
    """Japanese text with trailing runtime placeholders removed, so 「…してください: {{fields}}」 ends in ください."""
    return TRAILING_TOKENS.sub('',japanese).rstrip()


def role_aware_findings(role,english,japanese,policy,en_width,ja_width):
    out=[]
    if role in {'technical','accessibility','unknown'}:return out,None
    if not JA_TEXT.search(japanese):return out,None  # English fallback or code: the structural validator reports these
    tail=ending(japanese)
    if role in COMPACT:
        if JA_CONTROL_SENTENCE_END.search(tail):out.append(('control-sentence-ending','needs-review','A button, label, heading or status should be a short noun/action form, not a sentence.'))
        if role=='action' and JA_ACTION_VERB_END.search(tail):out.append(('action-verb-ending','needs-review','A button should end in the action noun (e.g. 保存), not する/します.'))
        if japanese.endswith('。'):out.append(('control-full-stop','info','Controls normally have no 。.'))
    sentence=english_is_sentence(english)
    # ui-writing.md allows a short confirmation question such as 選択項目を削除？
    short_question=role=='confirmation' and re.search(r'[？?]$',tail)
    if role in {'message','confirmation'} and sentence and not short_question and not JA_POLITE_END.search(tail):
        out.append(('message-note-style','needs-review','The English is a full sentence, but the Japanese ends like a note (no です/ます/ません/ください ending).'))
    # Hints, placeholders and empty-state text may be clipped instructions: no ending or request-form check.
    if role in {'message','confirmation'} and EN_REQUEST.search(english) and not JA_REQUEST.search(japanese):
        out.append(('request-form-missing','needs-review','The English asks the user to do something, but the Japanese has no request form (ください etc.).'))
    if role in SENTENCE and JA_FORMAL.search(japanese):
        out.append(('formal-phrasing','info','Stiff or roundabout phrasing; check whether a shorter natural form fits.'))
    if role in {'message','confirmation'} and re.search(r'[.!?]$',english.strip()) and not JA_FULLSTOP.search(tail):
        out.append(('sentence-full-stop-missing','info','The English sentence ends with punctuation; the Japanese has no 。.'))
    width=policy['widthBudget'];budget=None
    if role in set(width['roles']) and en_width>0:
        budget=max(width['minimumCells'],math.ceil(en_width*width['growthRatio']))
        if ja_width>budget and japanese not in set(policy['standardTerms']):
            over=ja_width-budget
            level='info' if over<=width.get('toleranceCells',2) else 'needs-review'
            out.append(('estimated-width-growth',level,f'Japanese is {over} cell(s) wider than the estimated budget for a compact control; check the real component.'))
    return out,budget


def role_aware_audit(source,target,configured,peers=None):
    policy=role_aware_settings(configured)
    en=dict(strings(source));ja=dict(strings(target))
    for key,decision in policy['provisionalRolesByKey'].items():
        if key not in en or decision['source']!=en[key]:raise ValueError('Provisional role source changed: '+key)
    rows=[];findings=[];role_counts=Counter();confidence_counts=Counter();basis_counts=Counter()
    for key,english in en.items():
        if key not in ja:continue
        japanese=ja[key]
        role,basis,confidence,notes=resolve_role(key,english,policy,peers)
        role_counts[role]+=1;confidence_counts[confidence]+=1;basis_counts[basis.split(':')[0]]+=1
        en_width,ja_width=display_cells(english),display_cells(japanese)
        found,budget=role_aware_findings(role,english,japanese,policy,en_width,ja_width)
        exception=policy['exceptionsByKey'].get(key)
        retained=check_exception(exception,english,japanese,key)
        for code,level,explanation in found:
            status='info' if level=='info' else 'retained-with-specific-reason' if code in retained else 'needs-review'
            findings.append({'key':key,'code':code,'level':level,'status':status,'role':role,'roleBasis':basis,'roleConfidence':confidence,
                'english':english,'japanese':japanese,'explanation':explanation,
                'reason':exception['reason'] if code in retained else None,
                'sourceLiteralCells':en_width,'targetLiteralCells':ja_width,'estimatedBudgetCells':budget})
        rows.append({'key':key,'english':english,'japanese':japanese,'role':role,'roleBasis':basis,'roleConfidence':confidence,'roleNotes':notes,
                     'sourceLiteralCells':en_width,'targetLiteralCells':ja_width,'estimatedBudgetCells':budget,'findingCodes':[c for c,_,_ in found]})
    findings.sort(key=lambda f:(CONFIDENCE_ORDER[f['roleConfidence']],0 if f['status']=='needs-review' else 1,f['key']))
    unresolved=[f for f in findings if f['status']=='needs-review']
    missing=sorted(set(en)-set(ja));extra=sorted(set(ja)-set(en))
    by_code=Counter(f['code'] for f in findings)
    return {'status':'incomplete-input-pair' if missing or extra else 'needs-ui-writing-review' if unresolved else 'no-unreviewed-heuristic-findings',
       'style':'role-aware','policy':policy,
       'counts':{'sourceStrings':len(en),'targetStrings':len(ja),'comparedStrings':len(rows),'missingTargetStrings':len(missing),
          'extraTargetStrings':len(extra),'findings':len(findings),'unreviewedFindings':len(unresolved),
          'infoFindings':sum(f['status']=='info' for f in findings),
          'skippedWithoutJapaneseText':sum(1 for r in rows if not JA_TEXT.search(r['japanese'])),'flaggedKeys':len({f['key'] for f in unresolved}),
          'findingsByCode':dict(sorted(by_code.items())),
          'lowConfidenceRoles':confidence_counts['low']},
       'roleCounts':dict(role_counts),'roleConfidenceCounts':dict(confidence_counts),'roleBasisCounts':dict(basis_counts),
       'peerEvidenceUsed':peers is not None,
       'actualUILayoutChecked':False,'pixelWidthMeasured':False,'runtimeVariableWidthMeasured':False,
       'limitations':['Roles come from the profile, key-name rules, same-English keys elsewhere or English shape; call sites are not inspected.',
                      'Low-confidence roles are listed first; confirm them in the profile (rolesByKey/rolesByPattern).',
                      'Display cells are a literal-text heuristic, not actual font or component width.',
                      'Placeholders/markup and their runtime rendering are not measured.',
                      'Info-level findings are suggestions and do not make the result unresolved.',
                      'No structural, business-meaning, terminology or native-speaker approval is provided.',
                      'The audit never edits or automatically shortens Japanese.'],
       'missingTargetKeys':missing,'extraTargetKeys':extra,'findings':findings,'strings':rows}


# ---------------------------------------------------------------- entry points

def audit(source,target,profile=None,peers=None):
    configured=(profile or {}).get('uiWriting',{})
    style=configured.get('style','role-aware')
    if style=='compact':return legacy_audit(source,target,configured)
    if style!='role-aware':raise ValueError('Unsupported UI-writing style: '+str(style))
    return role_aware_audit(source,target,configured,peers)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('source');parser.add_argument('target');parser.add_argument('--profile');parser.add_argument('--output')
    parser.add_argument('--peers',help='Duplicate-text report: same-English keys in other files/apps used as role evidence')
    parser.add_argument('--semantic-review',help='Semantic review: groups marked as separate meanings/roles never share roles')
    parser.add_argument('--application',help='application name of the source, for peer evidence')
    args=parser.parse_args()
    source,target=Path(args.source),Path(args.target)
    if source.suffix.lower()!='.json' or target.suffix.lower()!='.json':raise ValueError('UI-writing audit currently supports strict JSON only')
    if args.output and Path(args.output).resolve() in {source.resolve(),target.resolve()}:raise ValueError('Refusing to overwrite an input resource')
    peers=None
    if args.peers:
        peers=PeerIndex(load(Path(args.peers)),load(Path(args.semantic_review)) if args.semantic_review else None,args.application,source.as_posix())
    result=audit(load(source),load(target),load(Path(args.profile)) if args.profile else None,peers)
    if args.output:
        output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'status':result['status'],'style':result.get('style','compact'),'counts':result['counts'],'actualUILayoutChecked':False},ensure_ascii=False,indent=2))
