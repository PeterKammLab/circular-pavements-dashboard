"""Circular Pavements dashboard. Run from the cirlog project root:
    python -m streamlit run dashboard.py
Uses outputs created by 09_HU_model.ipynb in test_model/<scenario>/.
"""
from pathlib import Path
import time
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / 'dashboard_results'
if not RESULTS.exists():
    RESULTS = ROOT / 'test_model'
FLOW_ORDER = ['incoming_new', 'incoming_reused', 'outgoing_reuse', 'outgoing_processing']
FLOW_LABELS = {'incoming_new':'Incoming new','incoming_reused':'Incoming reused','outgoing_reuse':'Outgoing for reuse','outgoing_processing':'Outgoing for processing'}
FLOW_COLORS = {'incoming_new':'#a6cee3','incoming_reused':'#fdae61','outgoing_reuse':'#d95f0e','outgoing_processing':'#bdbdbd'}

st.set_page_config(page_title='Circular Pavements | Amsterdam', layout='wide')
st.markdown('''<style>
.stApp {background:#fafafa;color:#222}
.stButton > button[kind="primary"] {background:#1a1a1a;color:white;border:0;border-radius:8px;min-height:2.8rem}
.stButton > button[kind="primary"]:hover {background:#333;color:white;border:0}
.stButton > button[kind="primary"] {justify-content:flex-start !important;text-align:left !important;padding-left:14px !important}
.stButton > button[kind="primary"] p {text-align:left !important;width:100% !important;margin:0 !important}
.stButton > button[kind="primary"] [data-testid="stMarkdownContainer"] {width:100% !important;text-align:left !important}
.stButton > button[kind="primary"] [data-testid="stMarkdownContainer"] p {text-align:left !important;width:100% !important}
.stButton > button[kind="primary"] {display:flex !important;align-items:center !important;justify-content:flex-start !important}
[data-testid="stMetric"] {background:white;border:1px solid #e8e8e8;border-radius:9px;padding:14px}
</style>''', unsafe_allow_html=True)

# Dashboard header
header_left, header_right = st.columns([1.5, 1.5], gap="large")

with header_left:
    st.title("Circular Pavements")
    st.markdown(
        "Spatial modelling of transport, material reuse and "
        "environmental impact in Amsterdam’s road maintenance."
    )
    st.caption("TU Delft · AMS Institute")

with header_right:
    st.image(
        str(ROOT / "assets" / "circular_pavements_header.png"),
        use_container_width=True
    )

# Controls: changes are only committed on button click.
scenario_col, start_col, end_col, spacer_col = st.columns([2.5, 1.15, 1.15, 3.2], gap='medium')
with scenario_col:
    scenario = st.selectbox(
        'Scenario', ['baseline', 'linear', 'circular'],
        format_func=lambda s: {
            'baseline': 'Baseline · current reuse',
            'linear': 'Linear · no reuse',
            'circular': 'Circular · maximum reuse'
        }[s]
    )
with start_col:
    start_year = st.selectbox('Start year', list(range(2025, 2031)), index=0)
with end_col:
    end_options = list(range(start_year, 2031))
    end_year = st.selectbox('End year', end_options, index=len(end_options) - 1)

scenario_descriptions = {
    'linear': 'Linear: materials are supplied new, without reuse.',
    'baseline': 'Baseline: current material reuse practices.',
    'circular': 'Circular: maximum material reuse scenario.'
}
st.caption(scenario_descriptions[scenario])

button_col, _ = st.columns([1.25, 8.75])
with button_col:
    run = st.button('▶ Run Model', type='primary', use_container_width=True)

if run:
    # Remove previously displayed results while loading the new selection.
    with st.spinner('Running model...', show_time=False):
        time.sleep(3)
    st.session_state['selection'] = (scenario,start_year,end_year)
    st.rerun()
selection = st.session_state.get('selection')
if selection is None:
    st.stop()
scenario,start_year,end_year = selection

result_dir = RESULTS / scenario
flow_path = result_dir / 'logistics_flows_per_project_year.csv'
if not flow_path.exists():
    st.error('Results are not available for the selected scenario.')
    st.stop()

@st.cache_data(show_spinner=False)
def read_flows(path,mtime):
    return pd.read_csv(path)

flows = read_flows(str(flow_path),flow_path.stat().st_mtime).copy()
required = {'year','flow','tonnes','km','tkm'}
if not required.issubset(flows.columns):
    st.error('The selected scenario results are incomplete.')
    st.stop()
flows['year'] = pd.to_numeric(flows['year'],errors='coerce')
for col in ['tonnes','km','tkm','co2_tCO2']:
    if col in flows.columns:
        flows[col] = pd.to_numeric(flows[col],errors='coerce').fillna(0)
flows = flows[flows['year'].between(start_year,end_year)].copy()
if flows.empty:
    st.warning('No flows in the selected period.')
    st.stop()

incoming = flows[flows['flow'].isin(['incoming_new','incoming_reused'])]
reused = flows[flows['flow'].eq('incoming_reused')]
reuse_pct = 100*reused['tonnes'].sum()/incoming['tonnes'].sum() if incoming['tonnes'].sum()>0 else 0
projects = flows['project_key'].nunique() if 'project_key' in flows else (flows['project_name'].nunique() if 'project_name' in flows else None)
co2 = flows['co2_tCO2'].sum() if 'co2_tCO2' in flows else None
if co2 is None:
    em_file = result_dir / 'logistics_emissions_per_year.csv'
    if em_file.exists():
        em = pd.read_csv(em_file)
        em['year'] = pd.to_numeric(em['year'], errors='coerce')
        co2 = pd.to_numeric(em.loc[em['year'].between(start_year, end_year), 'total_co2'], errors='coerce').sum()

cols=st.columns(6)
metrics=[('Material flows',f"{flows['tonnes'].sum():,.0f} t",'Total transported material across incoming and outgoing flows; the same material may be counted in both directions.'),('Incoming reuse',f'{reuse_pct:.1f}%', 'Share of incoming material tonnes supplied as reused material.'),('Transport',f"{flows['km'].sum():,.0f} km",'Total vehicle distance travelled for material logistics.'),('Transport work',f"{flows['tkm'].sum():,.0f} tkm",'Tonne-kilometres: material mass multiplied by transport distance.'),('CO₂',f'{co2:,.1f} tCO₂' if co2 is not None else '—','Total modelled transport CO₂ emissions.'),('Projects',f'{projects:,}' if projects is not None else '—','Number of distinct projects with recorded material flows.')]
for col,(label,value,unit) in zip(cols,metrics):
    col.metric(label,value,help=unit)


st.subheader('Logistics network map')
map_file = result_dir / 'logistics_map_light_flows3.html'
if map_file.exists():
    html = map_file.read_text(encoding='utf-8')
    # Display the actual saved Folium map without rewriting tile URLs.
    # Rebuild it with notebook cells 22–23 after changing the basemap.
    components.html(html, height=620, scrolling=False)

else:
    st.info('Map not available for this scenario.')

st.subheader('Material reuse by material')


if 'material' in flows.columns:
    materials = ['Betontegel', 'Betonsteen', 'Gebakken Steen']

    m_in = incoming.groupby('material')['tonnes'].sum()
    m_re = reused.groupby('material')['tonnes'].sum()

    reuse_by_material = pd.Series({
        mat: (
            100 * m_re.get(mat, 0) / m_in.get(mat, 0)
            if m_in.get(mat, 0) > 0 else 0.0
        )
        for mat in materials
    })

    cols = st.columns(len(reuse_by_material))
    for col, (material, pct) in zip(cols, reuse_by_material.items()):
        col.metric(material, f'{pct:.1f}%')

left,right=st.columns(2)
with left:
    st.subheader('Transport distance')
    annual=flows.groupby('year',as_index=False)[['km','tkm']].sum()
    fig=px.line(annual,x='year',y='km',markers=True,labels={'year':'Year','km':'Vehicle-km'})
    fig.update_traces(line_color='#222222')
    fig.update_layout(template='plotly_white',margin=dict(l=10,r=10,t=15,b=10),xaxis=dict(dtick=1))
    st.plotly_chart(fig,use_container_width=True)
with right:
    st.subheader('Material flow composition')
    composition=flows.groupby(['year','flow'],as_index=False)['tonnes'].sum()
    fig=px.bar(composition,x='year',y='tonnes',color='flow',barmode='stack',category_orders={'flow':FLOW_ORDER},color_discrete_map=FLOW_COLORS,labels={'year':'Year','tonnes':'Tonnes','flow':'Flow'})
    fig.update_layout(template='plotly_white',margin=dict(l=10,r=10,t=15,b=10),xaxis=dict(dtick=1))
    st.plotly_chart(fig,use_container_width=True)

st.download_button('Download filtered flows (CSV)',data=flows.to_csv(index=False).encode('utf-8'),file_name=f'circular_pavements_{scenario}_{start_year}_{end_year}.csv',mime='text/csv')



st.divider()
st.caption('Based on “Towards Circular Pavements: Spatial Modelling of Transport, Material Reuse and Environmental Impact in Amsterdam’s Road Maintenance”.')
st.caption('Petar Koljenšić¹ ², Felix Fröhling¹, Ruben Vrijhoef¹ · ¹ TU Delft, Faculty of Architecture and the Built Environment · ² AMS Institute')
st.caption('Funded by De Nieuwe Straat, part of the TBL Programme, supported by the Dutch Government and managed by AMS Institute.')
