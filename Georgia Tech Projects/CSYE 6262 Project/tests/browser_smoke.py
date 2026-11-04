"""Browser interaction checks with explicitly synthetic API fixtures, never production data.
Run a local server first; see README. Requires Playwright and Chromium.
"""
import json
import os

from playwright.sync_api import sync_playwright, expect

BASE = os.getenv('PRODUCTMATCH_TEST_URL', 'http://127.0.0.1:8011')
A = {'id':1,'source_id':'test-1','title':'Fixture laptop A','brand':'Lenovo','description':'16GB RAM 1TB SSD','price':100,'currency':'USD','seller':'Vendor A'}
B = dict(A,id=2,source_id='test-2',title='Fixture laptop B',price=90,seller='Vendor B')
C = dict(A,id=3,source_id='test-3',title='Fixture laptop C',price=80,seller='Vendor C',description='8GB RAM 1TB SSD')
D = dict(A,id=4,source_id='test-4',title='Fixture unknown price',price=None,currency='EUR',seller='Vendor D')
MODEL = {'id':'fixture','version':'test-only','name':'Synthetic UI fixture','available':True,'message':None,
         'capabilities':{'continuous_score':True,'threshold':True,'probability':False,'score_type':'decision_score','default_threshold':0.25}}

def result(score):
    return {'is_match':score>=0.25,'prediction':'Match' if score>=0.25 else 'Not a Match',
            'raw_score':score,'score_type':'decision_score','threshold':0.25,'model_id':'fixture','model_version':'test-only'}

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
    page = browser.new_page(viewport={'width':1440,'height':1000})
    errors=[]
    page.on('pageerror',lambda error: errors.append(str(error)))
    # First exercise the actual startup page without mocked APIs.
    page.goto(BASE)
    expect(page.locator('#model-status')).not_to_have_text('Checking model availability…')
    expect(page.locator('#candidate-empty')).to_be_visible()
    expect(page.locator('#vendor-filter')).to_be_disabled()
    page.locator('#attributes-btn').click()
    expect(page.locator('#manual-entry')).to_have_attribute('open', '')
    page.locator('#example-btn').click()
    page.locator('#attributes-btn').click()
    expect(page.locator('#attribute-body tr')).to_have_count(5)
    expect(page.locator('#evaluation-content')).to_contain_text('No verified evaluation')
    print('PASS: actual startup state, manual attributes, evaluation empty state')
    def fulfill(route,data): route.fulfill(status=200,content_type='application/json',body=json.dumps(data))
    page.route('**/models',lambda route:fulfill(route,{'active_model':'fixture','models':[MODEL]}))
    page.route('**/search?*',lambda route:fulfill(route,{'count':1,'results':[A]}))
    page.route('**/candidates/1*',lambda route:fulfill(route,{'reference':A,'model':MODEL,'candidates':[
        {'product':B,'prediction':result(0.8)},{'product':C,'prediction':result(0.1)},{'product':D,'prediction':result(-0.3)}]}))
    official=dict(result(0.8),attributes=[{'attribute':'RAM','a':'16GB','b':'8GB','status':'conflict'}])
    page.route('**/predict',lambda route:fulfill(route,official))
    evaluated = {'id':'fixture','name':'Synthetic UI fixture','version':'test-only','evaluation':{
        'dataset_id':'synthetic-browser-fixture-only','split':'test fixture','procedure':'UI test, not research results',
        'metrics':{'accuracy':0.8,'precision':0.75,'recall':1.0,'f1':0.8571},
        'confusion_matrix':[[1,1],[0,3]],
        'thresholds':[{'threshold':0.1,'precision':0.75,'recall':1.0,'fp':1,'fn':0},
                      {'threshold':0.5,'precision':1.0,'recall':0.6667,'fp':0,'fn':1}]}}
    page.route('**/evaluation',lambda route:fulfill(route,{'models':[evaluated,
        {'id':'unreported','name':'Unreported fixture','version':'test-only','evaluation':None}]}))
    submissions=[]
    def feedback(route):
        submissions.append(route.request.post_data_json)
        fulfill(route,{'saved':True,'duplicate':False})
    page.route('**/feedback',feedback)
    page.reload()
    expect(page.locator('#model-status')).to_contain_text('Ready')
    page.locator('#search-query').fill('Fixture laptop')
    page.locator('#search-btn').click()
    page.get_by_role('button',name='Explore matches',exact=True).click()
    expect(page.locator('#visible-count')).to_have_text('3')
    expect(page.locator('#candidate-chart circle')).to_have_count(3)
    expect(page.locator('#match-count')).to_have_text('1')
    print('PASS: search, reference selection, candidate scores, scatterplot')
    page.locator('#currency-filter').select_option('USD')
    expect(page.locator('#candidate-chart circle')).to_have_count(2)
    expect(page.locator('#lowest-price')).to_have_text('90.00 USD')
    page.locator('#threshold').evaluate('(element) => {element.value=0; element.dispatchEvent(new Event("input",{bubbles:true}));}')
    expect(page.locator('#match-count')).to_have_text('2')
    expect(page.locator('#lowest-price')).to_have_text('80.00 USD')
    page.locator('#candidate-chart circle').nth(1).focus()
    page.keyboard.press('Enter')
    expect(page.locator('#b-title')).to_have_value('Fixture laptop C')
    expect(page.locator('#attribute-body')).to_contain_text('Conflict')
    expect(page.locator('#pair-result')).to_be_hidden()
    print('PASS: currency isolation, threshold counts/prices, keyboard-linked attribute selection')
    page.locator('#vendor-filter').select_option('Vendor B')
    expect(page.locator('#visible-count')).to_have_text('1')
    page.locator('#reset-filters').click()
    expect(page.locator('#visible-count')).to_have_text('3')
    expect(page.locator('#threshold-value')).to_have_text('0.2500')
    page.locator('#compare-btn').click()
    expect(page.locator('#pair-result')).to_contain_text('Official prediction: Match')
    page.get_by_role('button',name='Unsure',exact=True).click()
    expect(page.locator('#feedback-status')).to_contain_text('Review saved')
    assert submissions[0]['model_id']=='fixture'
    assert submissions[0]['product_b']['source_id']=='test-3'
    page.locator('#manual-entry > summary').click()
    page.locator('#b-title').fill('Changed pair')
    expect(page.locator('#pair-result')).to_be_hidden()
    expect(page.get_by_role('button',name='Unsure',exact=True)).to_be_disabled()
    print('PASS: filter reset, official prediction, feedback payload, stale-result invalidation')
    # Label-only models still permit selection, without invented scores or threshold controls.
    label_model=dict(MODEL,capabilities={'continuous_score':False,'threshold':False,'probability':False,'score_type':None,'default_threshold':None})
    page.route('**/candidates/1*',lambda route:fulfill(route,{'reference':A,'model':label_model,'candidates':[
        {'product':B,'prediction':dict(result(0.8),raw_score=None,score_type=None,threshold=None)}]}))
    page.get_by_role('button',name='Explore matches',exact=True).click()
    expect(page.locator('#threshold')).to_be_disabled()
    expect(page.locator('#candidate-chart')).to_contain_text('Continuous scores are unavailable')
    expect(page.locator('#candidate-list .candidate-row')).to_have_count(1)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile horizontal overflow'
    print('PASS: label-only model fallback and mobile layout')
    expect(page.locator('#evaluation-content')).to_contain_text('synthetic-browser-fixture-only')
    expect(page.locator('#evaluation-content table')).to_contain_text('Different')
    page.locator('#evaluation-tab').click()
    expect(page.locator('#workspace-view')).to_be_hidden()
    page.locator('#evaluation-content input[type=range]').fill('1')
    expect(page.locator('#evaluation-content')).to_contain_text('Threshold 0.5')
    expect(page.locator('#evaluation-content svg circle')).to_have_count(2)
    page.locator('#evaluation-model').select_option('unreported')
    expect(page.locator('#evaluation-content')).to_contain_text('No verified evaluation')
    print('PASS: labeled-fixture metrics, confusion matrix, threshold curve and version selection')
    assert not errors,errors
    print('PASS: no browser JavaScript errors')
    browser.close()
