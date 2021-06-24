#%%
import mariadb, sys, datetime
import matplotlib.pyplot as plt 
import matplotlib.dates as md
import pandas as pd
import numpy as np
from misc import trc_mean
from sklearn.linear_model import LinearRegression

def getConnDB():
    conn= None
    try:
        conn = mariadb.connect(
            user="farmer",
            password="!SSUfarm0690",
            host="220.149.87.248",
            port=3307,
            database="livfarm"

        )
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Platform: {e}")
        sys.exit(1)
    return(conn)

def duplicate_water_pipes(df_water):
    df_dupl = df_water.loc[df_water['pipe']==2].copy()
    df_dupl.loc[:,'pipe'] = 1
    df_dupl2 = df_water.loc[df_water['pipe']==3].copy()
    df_dupl2.loc[:,'pipe'] = 4
    result = pd.concat([df_water, df_dupl, df_dupl2])
    return(result)

def getTimedRecords(conn, start, end, interval):
    cur = conn.cursor()
    cur.execute("SELECT timestamp, site, rack, floor, pipe, temperature, ec, ph, flowrate FROM `water.tab` WHERE timestamp>= ? AND timestamp<?", (start, end))
    df_water = pd.DataFrame(cur.fetchall(), columns=['timestamp', 'site', 'rack', 'floor', 'pipe', 'temp_w', 'ec', 'ph', 'fr'])
    cur.execute("SELECT timestamp, site, rack, floor, pipe, pot, pixels, bbx, bby, radius, imgfile FROM `growth.tab` WHERE timestamp>= ? AND timestamp<?", (start, end))
    df_growth = pd.DataFrame(cur.fetchall(), columns=['timestamp', 'site', 'rack', 'floor', 'pipe', 'pot', 'pixels', 'bx', 'by', 'radius', 'img'])
    cur.execute("SELECT timestamp, site, rack, floor, pipe, pot, temperature, humidity, brightness FROM `atmos.tab` WHERE timestamp>= ? AND timestamp<?", (start, end))
    df_atmos = pd.DataFrame(cur.fetchall(), columns=['timestamp', 'site', 'rack', 'floor', 'pipe', 'pot', 'temp_a', 'humid', 'bright'])

    df_water = duplicate_water_pipes(df_water)

    agg_water = df_water.groupby([pd.Grouper(key='timestamp', freq=interval, origin=start),'site','rack','floor','pipe']).mean()
    agg_growth = df_growth.groupby([pd.Grouper(key='timestamp', freq=interval, origin=start),'site','rack','floor','pipe','pot']).mean()
    agg_atmos = df_atmos.groupby([pd.Grouper(key='timestamp', freq=interval, origin=start),'site','rack','floor','pipe','pot']).mean()

    return(agg_water.reset_index(), agg_growth.reset_index(), agg_atmos.reset_index())

def getAggTable(conn, start, end, interval = 10):
    (df_water, df_growth, df_atmos) = getTimedRecords(conn, start, end, str(interval)+'min')
    df_ga = pd.merge(df_growth, df_atmos, on=['timestamp','site','rack','floor','pipe','pot'])
    df_gaw = pd.merge(df_ga, df_water.drop(columns=['floor']), on=['timestamp','site','rack','pipe'], how='left')
    return(df_gaw)


def drawPlots(subset, ylabel, ax):

    ax.plot(subset['timestamp'], subset[ylabel])
    xfmt = md.DateFormatter('%d/%H')
    ax.xaxis.set_major_formatter(xfmt)
    # ax.set_xlim(min(df['timestamp']), max(df['timestamp']))
    # plt.xticks(rotation=25)
    # plt.title(ylabel+':'+'/'.join(map(str,[rack, floor, pipe, pot])))
    # plt.show()

    # return(subset)

def drawMultiPlots(dfs, ylabels, darkdrops):
    
    
    fig, axs = plt.subplots(len(ylabels),len(dfs))
    # print(axs.size)
    fig.set_size_inches(6*len(dfs), 12)
    # fig.suptitle('/'.join(map(str,df_idx.index[0])))
    for j, df in enumerate(dfs):
        subset = df[df['bright']>darkdrops[j]].copy()
        axs[0,j].set_title('/'.join(map(str,subset.index[0])))
        for i, label in enumerate(ylabels):
            drawPlots(subset, label, axs[i,j])

def getStagedData(dfa, interval = '24H', rampup = '60min', brightp = 15000):
    df = dfa.reset_index(drop=True)
    startT = min(df['timestamp'])+pd.Timedelta(rampup)
    stages = pd.date_range(start = startT,end  = max(df['timestamp']), freq=interval)
    
    df_staged = df[df['timestamp'].isin(stages)]
    # print(df_staged)
    r_growth = df_staged[['pixels','bx','by','radius']].pct_change()[1:]+1
    r_growth['timestamp'] = df_staged['timestamp'][:(len(r_growth.index)-1)]
    avg_env = df[['timestamp','temp_a','humid','temp_w','ec','ph','bright']].groupby([pd.Grouper(key='timestamp', freq='12H', origin=startT)]).mean()[1:]
    on_time = df[['timestamp','bright']].groupby([pd.Grouper(key='timestamp', freq='12H', origin=startT)]).agg(lambda x: sum(x>brightp))[1:]
    # return(r_growth, avg_env,on_time)
    return(r_growth.merge(avg_env, on='timestamp').merge(on_time, on='timestamp'))
    # return(pd.DataFrame([stages[2:],r_growth]))
    # return(pd.concat([r_growth.reset_index(drop=True),avg_env,on_time], axis=1))




# %%
# batch records
# 5.25~6.1 1차
# 6.2~6.8 2차 3시간/9시간
# 6.9.12~ 6.21 3차 2시간/8시간
# Get Cursor
conn = getConnDB()

# df = getAggTable(conn, "2021-05-27 00:00:00", "2021-06-27 15:00:00", 1)
df1 = getAggTable(conn, "2021-06-09 12:00:00", "2021-06-20 14:00:00", 10)
df1.loc[df1['bright']>20000,'bright']=20000
df_idx1 = df1.set_index(['site','rack','floor','pipe','pot']).sort_index()


df2 = getAggTable(conn, "2021-06-02 12:00:00", "2021-06-08 14:00:00", 10)
df2.loc[df2['bright']>20000,'bright']=20000
df_idx2 = df2.set_index(['site','rack','floor','pipe','pot']).sort_index()


df3 = getAggTable(conn, "2021-05-26 12:00:00", "2021-06-01 14:00:00", 10)
df_idx3 = df3.set_index(['site','rack','floor','pipe','pot']).sort_index()
# drawPlots(df,'pixels','SSU',1,3,2,2)
conn.close()
#%%
exp_data = pd.concat([getStagedData(df_idx1.loc['SSU', 1, 3, 2, 3]),getStagedData(df_idx1.loc['SSU', 1, 3, 3, 3]),getStagedData(df_idx1.loc['SSU', 1, 2, 2, 4]),getStagedData(df_idx1.loc['SSU', 1, 2, 3, 4])])
exp_data = pd.concat([exp_data,getStagedData(df_idx2.loc['SSU', 1, 3, 2, 2]),getStagedData(df_idx2.loc['SSU', 1, 3, 3, 2]),getStagedData(df_idx2.loc['SSU', 1, 2, 2, 4]),getStagedData(df_idx2.loc['SSU', 1, 2, 3, 4])])
# exp_data = pd.concat([exp_data,getStagedData(df_idx3.loc['SSU', 1, 3, 2, 2]),getStagedData(df_idx3.loc['SSU', 1, 3, 3, 2]),getStagedData(df_idx3.loc['SSU', 1, 2, 1, 9]),getStagedData(df_idx3.loc['SSU', 1, 2, 4, 9])])
# exp_data = pd.concat([getStagedData(df_idx.loc['SSU', 1, 2, 2, 4]),getStagedData(df_idx.loc['SSU', 1, 2, 3, 4])])
#%%


df_todraw = (df_idx.loc['SSU', 1, 3, 2, 3],df_idx.loc['SSU', 1, 3, 3, 3],df_idx.loc['SSU', 1, 2, 2, 4],df_idx.loc['SSU', 1, 2, 3, 4])
# df_todraw = (df_idx.loc['SSU', 1, 2, 4, 9])
drawMultiPlots(df_todraw,['pixels','bright','humid','ec'], (18000,18000,18000,18000))
# drawMultiPlots(df_todraw,['pixels','bright','humid','ec'], (9000))
fig = plt.figure()


# df_sub = drawPlots(df,'bx','SSU',1,3,3,2,20000)
# df_sub = drawPlots(df,'bright','SSU',1,3,3,2,20000)
# %%
fig = plt.figure()
ax = fig.add_subplot(1, 1, 1)

ax.plot((df_idx.loc['SSU', 1, 2, 2, 4])['timestamp'],(df_idx.loc['SSU', 1, 2, 2, 4])['pixels'], color='tab:blue')
ax.plot((df_idx.loc['SSU', 1, 2, 3, 4])['timestamp'],(df_idx.loc['SSU', 1, 2, 3, 4])['pixels'], color='tab:orange')

# %%

exp_data = exp_data.dropna()
line_fitter = LinearRegression()
X=exp_data[['bright_y','temp_w','temp_a','ec']]
y=exp_data['pixels']
line_fitter.fit(X, y)
print(line_fitter.score(X,y))
# plt.scatter(exp_data['bright_x'], exp_data['pixels'])
# X= np.arange(0,15000,1)
plt.scatter(y,line_fitter.predict(X))
plt.plot(y,y)
# %%

# %%
