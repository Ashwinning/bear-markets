import streamlit as st
st.set_page_config(
     page_title="Tracking the Bear Market",
     page_icon="🐻",
     layout="wide",
 )

#st.title('Tracking the Bear Market')
st.markdown("<div style='text-align: center; padding-bottom: 36px;'><h1 style='padding: 5px;'>Tracking the Bear Market</h1>(Auto-updated daily)</div> ", unsafe_allow_html=True)

import json

with open('GSPC-Yahoo-Finance.json') as f:
	data = json.load(f)

import pandas as pd

df = pd.DataFrame()

df['timestamp'] = data['chart']['result'][0]['timestamp']

quotes = data['chart']['result'][0]['indicators']['quote'][0]

for quote in quotes.keys():
	df[quote] = quotes[quote]

df['adjclose'] = data['chart']['result'][0]['indicators']['adjclose'][0]['adjclose']

df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')

# Calculate bear markets

inBearMkt = False
lastPeak = None
bearMarketThreshold = 0.2 # Decline since peak when the market is officially bearish

bearMarkets = []

for i, day in df.iterrows():
	if lastPeak == None:
		lastPeak = day.to_dict()

	if not inBearMkt:
		if day['close'] > lastPeak['close']:
			lastPeak = day.to_dict()
		if day['close'] <= lastPeak['close'] * (1-bearMarketThreshold):
			inBearMkt = True
			bearMarkets.append({'start': lastPeak['timestamp'], 'trigger': day['timestamp']})
	
	if inBearMkt:
		if day['close'] >= lastPeak['close']:
			bearMarkets[-1]['end'] = day['timestamp']
			inBearMkt = False
	
# If we are currently in a bear market, add an end to the current bear market
if 'end' not in bearMarkets[-1].keys():
	bearMarkets[-1]['end'] = df.iloc[-1]['timestamp']

import plotly.graph_objects as go

from datetime import date, datetime
from dateutil import relativedelta

def YMDBetweenDates(date2, date1):
	diff = relativedelta.relativedelta(date2, date1)
	output = ''
	ymd = {}
	ymd['yrs'] = diff.years
	ymd['mos'] = diff.months
	ymd['days'] = diff.days
	for x in ymd.items():
		if x[1] < 1:
			continue
		if x[1] < 2:
			output += str(x[1]) + ' ' + str(x[0])[:-1] + ' '
		else:
			output += str(x[1]) + ' ' + str(x[0]) + ' '
	return output


bearData = []

for bear in bearMarkets:
	mask = (df['timestamp'] >= bear['start']) & (df['timestamp'] <= bear['end'])
	bearData.append(df.loc[mask])

for data in bearData:
	data['days'] = range(len(data))
	pos = data.columns.get_loc('close')
	data['change'] =  (data.iloc[1:, pos] / data.iat[0, pos]) -1



currentMarket = df[df['timestamp'] > pd.Timestamp(2022, 1, 2)]
currentMarket['days'] = range(len(currentMarket))
pos = currentMarket.columns.get_loc('close')
currentMarket['change'] =  (currentMarket.iloc[1:, pos] / currentMarket.iat[0, pos]) - 1

_, col1, col2, col3, _ = st.columns([3,1,1,1,3])

with col1:
	st.metric('Days since last peak', f"{ (datetime.now() - currentMarket.iloc[0]['timestamp']).days} days", delta=None)

with col2:  
	st.metric('Delta since last peak', f"{(currentMarket.iloc[-1]['close'] / currentMarket.iloc[0]['close']) -1:0.2%}", delta=None)

with col3:  
	st.metric('Max. drawdown since last peak', f"{(min(currentMarket['close']) / currentMarket.iloc[0]['close']) -1:0.2%}", delta=None)



bearFigs = go.Figure()

important = ['Dec-1961', 'Mar-2000', 'Oct-2007', 'Feb-2020']

for data in bearData[:-1]:
	name = name=data.iloc[0]['timestamp'].strftime("%b-%Y")
	bearFigs.add_trace(go.Scatter(x=data['days'], y=data['change'], mode='lines', name=name, opacity=0.4 if name in important else 0.15,
		hovertemplate=[f" {x['change']:.1%} ({x['timestamp'].strftime('%b %d, %Y')})<br> {(x['days'])} trading days since peak" for i, x in data.iterrows()]
	))

bearFigs.add_trace(go.Scatter(x=currentMarket['days'], y=currentMarket['change'], mode='lines', name='Current Market', line={'width': 3, 'color': 'darkblue'},
	hovertemplate=[f" {x['change']:.1%} ({x['timestamp'].strftime('%b %d, %Y')})<br> {(x['days'])} trading days since peak" for i, x in currentMarket.iterrows()]
))

bearFigs.update_layout(xaxis={'range':[0, 1912], 'showgrid':False}, 
	yaxis=dict(tickformat="0.2%", range=[-0.6, 0.05], showgrid=False),
	legend_title="Bear Markets<br><i>(starting month)</i>",
	title="Where are we compared to previous bear markets?<br>S&P500 (daily close)",
	title_font_size=24,
	xaxis_title = "Trading days since last peak",
	yaxis_title = "Drawdown",
	template='none',
	paper_bgcolor="rgb(255,255,255)", plot_bgcolor="rgb(255,255,255)",
	legend_traceorder="reversed",
	width=1650, height=455
)

_, col1, _ = st.columns([1,30,1])

with col1:
	st.plotly_chart(bearFigs, width=1650)


fig = go.Figure(data=go.Scatter(x = df.timestamp, y = df.close))
for i, data in enumerate(bearData):
	# Add a shape whose x and y coordinates refer to the domains of the x and y axes
	fig.add_vrect(x0=data.iloc[0]['timestamp'], x1=data.iloc[-1]['timestamp'],
	fillcolor='grey', opacity=0.15, layer="below", line_width=0)
	# Name
	if i != len(bearData)-1:
		fig.add_annotation(x=data.iloc[0]['timestamp'] + (data.iloc[-1]['timestamp']-data.iloc[0]['timestamp'])/2, 
			y=0,
			text= data.iloc[0]['timestamp'].strftime("%b-%Y"),
			align='left',
			showarrow=False,
			yshift=260,
			xshift=-5,
			xanchor='center'
			)

fig.update_yaxes(type='log')
fig.update_xaxes(showgrid=False)
fig.update_yaxes(showgrid=False)
fig.update_layout(template = 'none',
	legend_title="Bear Markets<br><i>(starting month)</i>",
	title="Bear markets since The Great Depression<br>S&P500",
	title_font_size=24,
	yaxis_title = "S&P500<br>Daily Close (Log Scale)",
	paper_bgcolor="rgb(255,255,255)", plot_bgcolor="rgb(255,255,255)",
	yaxis=dict(tickformat="$0.2f"),
	width=1650,
	)

_, col1, _ = st.columns([1,30,1])

with col1:
	st.plotly_chart(fig, width=1650)


_, col1, _ = st.columns([1,5,1])
with col1:
	'''
	### Comparing the current market with previous bear markets
	'''
	defaultOpenCharts = ['Feb-2020','Oct-2007', 'Dec-1961']
	for i, data in reversed(list(enumerate(bearData[:-1]))):
		name = data.iloc[0]['timestamp'].strftime("%b-%Y")
		with st.expander(name, expanded=True if name in defaultOpenCharts else False):
			fig = go.Figure()
			fig.add_trace(go.Scatter(x=currentMarket['days'], y=currentMarket['change'], mode='lines', name='Current Market', line={'width': 3, 'color': 'darkblue'}, 
				hovertemplate=[f" {x['change']:.1%} ({x['timestamp'].strftime('%b %d, %Y')})" for i, x in currentMarket.iterrows()]
				))
			fig.add_trace(go.Scatter(x=bearData[i]['days'], y=bearData[i]['change'], mode='lines', name=name,
				hovertemplate=[f" {x['change']:.1%} ({x['timestamp'].strftime('%b %d, %Y')})" for i, x in bearData[i].iterrows()]
				))

			minCandle = bearData[i][bearData[i].close == bearData[i].close.min()]

			# Peak
			fig.add_annotation(x=0, 
				y=0,
				text=f'''┌ Peak''',
				align='left',
				showarrow=False,
				yshift=9,
				xshift=-5,
				xanchor='left'
				)

			# Market bottom
			fig.add_annotation(x=minCandle['days'].values[0], 
				y=minCandle['change'].values[0],
				text=f'''└ {minCandle['change'].values[0]:.1%}, {YMDBetweenDates(minCandle.iloc[0]['timestamp'], bearData[i].iloc[0]['timestamp'])}since peak ({minCandle.iloc[0]['days']} trading days)''',
				align='left',
				showarrow=False,
				yshift=-8,
				xshift=-6,
				xanchor='left'
				)

			# Cycle end
			fig.add_annotation(x=bearData[i].iloc[-1]['days'], 
				y=bearData[i].iloc[-1]['change'],
				text=f'''{YMDBetweenDates(bearData[i].iloc[-1]['timestamp'], bearData[i].iloc[0]['timestamp'])}since peak ({bearData[i].iloc[-1]['days']} trading days)   <br>
				{YMDBetweenDates(bearData[i].iloc[-1]['timestamp'], minCandle.iloc[0]['timestamp'])}since market bottom ({bearData[i].iloc[-1]['days'] - minCandle.iloc[0]['days']} trading days) ┐''',
				align='right',
				showarrow=False,
				yshift=17,
				xshift=7,
				xanchor='right',
				ax=0, ay=0
				)

			fig.update_layout( 
				yaxis=dict(tickformat="0.2%"),
				xaxis_title = "Trading days since last peak 🠆",
				yaxis_title = "🠄 Drawdown",
				template='simple_white',
				paper_bgcolor="rgb(255,255,255)", plot_bgcolor="rgb(255,255,255)",
				legend_traceorder="reversed",
				hovermode='x unified',
				margin=dict(t=50),
				width=1200
			)
			st.markdown(f"##### {name} vs Present Day (since 3 Jan '22)")
			st.plotly_chart(fig, width=1200)

'''

''' 
st.markdown("""<h6 style='text-align: center;'><a href='http://twitter.com/ashwinning'>Ashwin Sinha</a></h6>""", unsafe_allow_html=True)