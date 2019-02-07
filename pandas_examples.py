# -*- coding: utf-8 -*-
"""
Created on Wed Feb  6 16:06:51 2019

pandas
pip install pandas
"""

#import pandas as pd
import datetime
import pandas_datareader.data as web  
#we import pandas.io.data as web, because we're going to use this to pull data from the internet
from pandas_datareader.data import Options

import matplotlib.pyplot as plt
from matplotlib import style
style.use('fivethirtyeight')


start = datetime.datetime(2010, 1, 1)
end = datetime.datetime.now()

df = web.DataReader("XOM", "yahoo", start, end)
#This pulls data for Exxon from the Morningstar API
#print(df.head())

df.reset_index(inplace=True)
df.set_index("Date", inplace=True)
df = df.drop("Symbol", axis=1)

print(df.head())

df['High'].plot()
plt.legend()
plt.show()


options_prices = Options("XOM", "yahoo")
options_df = options_prices.get_options_data(expiry=options_prices.expiry_dates[0])
print(options_df.tail())


#########################
#dictionary to a dataframe using pandas
import pandas as pd

web_stats = {'Day':[1,2,3,4,5,6,7,8,9],
             'Visitors':[43,34,65,56,29,76,78,45,23],
             'Bounce Rate':[65,67,78,65,45,52,34,65,87]}

df = pd.DataFrame(web_stats)
df.head()
print(df.tail())
print(df.tail(2))

df.set_index('Day', inplace=True)
df.head()

df = df.set_index('Day')
df.head()
#notice how "Day" is lower than the other column headers, this is done to denote the index

print(df['Visitors'])
print(df.Visitors)

df.plot(); plt.show()

df['Visitors'].plot(); plt.show()

print(df[['Visitors','Bounce Rate']])

##############################################

df = pd.read_csv('sample1.csv')
print(df.head())

df.set_index('ID', inplace = True)

df.to_csv('newcsv2.csv')  #Create the new CSV file from dataframe
df['Name'].to_csv('newcsv2.csv') #Create the new CSV file from specific column of dataframe
df = pd.read_csv('newcsv2.csv', index_col=0)
df.columns = ['columnnamechange']
df.to_html('example.html')

df = pd.read_csv('newcsv2.csv', names = ['ID','Name','Designation','Office Email','Phone(Malaysia)','Status','Created By','Action'])
print(df.head())

df.rename(columns={'Name':'Name2121'}, inplace=True)
print(df.head())
#####################################################

fiddy_states = pd.read_html('https://simple.wikipedia.org/wiki/List_of_U.S._states')
print(fiddy_states)
print(fiddy_states[0])

for abbv in fiddy_states[0][0][1:]:
    print(str(abbv))
#####################################################
df1 = pd.DataFrame({'HPI':[11,12,13,14],
                    'Int_rate':[2, 3, 2, 2],
                    'US_GDP_Thousands':[50, 55, 65, 55]},
                   index = [2001, 2002, 2003, 2004])

df2 = pd.DataFrame({'HPI':[21,22,23,25],
                    'Int_rate':[2, 3, 2, 2],
                    'US_GDP_Thousands':[50, 55, 65, 55]},
                   index = [2005, 2006, 2007, 2008])

df3 = pd.DataFrame({'HPI':[31,32,34,36],
                    'Int_rate':[2, 3, 2, 2],
                    'Low_tier_HPI':[50, 52, 50, 53]},
                   index = [2001, 2002, 2003, 2004])

concat = pd.concat([df1,df2,df3])
print(concat)

df4 = df1.append(df2)
print(df4)

s = pd.Series([41,2,440], index=['HPI','Int_rate','US_GDP_Thousands'])
df4 = df1.append(s, ignore_index=True)
print(df4)


print(pd.merge(df1,df3, on='HPI'))
df4.set_index('HPI', inplace=True)
print(df4)

print(pd.merge(df1,df2, on=['HPI','Int_rate']))

joined = df1.join(df3, how="outer")
print(joined)

merged = pd.merge(df1,df3, on='Year')
print(merged)

merged = pd.merge(df1,df3, on='HPI', how='left')   #how='outer' 'right' 'inner'
merged.set_index('HPI', inplace=True)
print(merged)
#####################################################
