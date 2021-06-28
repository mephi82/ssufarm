#%%
import mariadb, sys, datetime
import matplotlib.pyplot as plt 
import matplotlib.dates as md
import pandas as pd
import numpy as np
from misc import trc_mean
from sklearn.linear_model import LinearRegression
from scipy import stats

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

def getStagedData(dfa, interval = '24H', rampup = '60min', brightp = 15000, lag = 0):
    df = dfa.reset_index(drop=True)
    startT = min(df['timestamp'])+pd.Timedelta(rampup)
    stages = pd.date_range(start = startT,end  = max(df['timestamp']), freq=interval)
    
    df_staged = df[df['timestamp'].isin(stages)]
    # print(df_staged)

    r_growth = df_staged[['pixels','bx','by','radius']].pct_change().shift(-1)
    r_growth.columns = ['pct_pixels','pct_bx','pct_by','pct_radius']
    df_staged = pd.concat([df_staged[['timestamp','pixels','bx','by','radius']],r_growth],axis=1)

    df_staged = df_staged[df_staged['timestamp'].diff().shift(-1)<=pd.Timedelta(interval)]
    df_staged = df_staged[df_staged['pct_pixels']>0]
    df_staged = df_staged[stats.zscore(df_staged['pct_pixels'])<2]
    # df_staged['timestamp'].diff().shift(-1)>pd.Timedelta(interval)
    # r_growth = (df_staged[['pixels','bx','by','radius']].pct_change()[1:]+1).reset_index(drop=True)
    # r_growth['timestamp'] = df_staged['timestamp'][:len(r_growth.index)].values
    
    avg_env = df[['timestamp','temp_a','humid','temp_w','ec','ph','bright']].groupby([pd.Grouper(key='timestamp', freq=interval, origin=startT)]).mean()[1:]
    on_time = df[['timestamp','bright']].groupby([pd.Grouper(key='timestamp', freq=interval, origin=startT)]).agg(lambda x: sum(x>brightp))[1:]
    
    # return(r_growth, avg_env,on_time)
    return(df_staged.merge(avg_env.shift(lag), on='timestamp').merge(on_time.shift(lag), on='timestamp'))
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


df2 = getAggTable(conn, "2021-06-03 00:00:00", "2021-06-08 14:00:00", 10)
df2.loc[df2['bright']>20000,'bright']=20000
df_idx2 = df2.set_index(['site','rack','floor','pipe','pot']).sort_index()


df3 = getAggTable(conn, "2021-05-26 12:00:00", "2021-06-01 14:00:00", 10)
df_idx3 = df3.set_index(['site','rack','floor','pipe','pot']).sort_index()
# drawPlots(df,'pixels','SSU',1,3,2,2)
conn.close()

#%%
df_todraw = (df_idx.loc['SSU', 1, 3, 2, 3],df_idx.loc['SSU', 1, 3, 3, 3],df_idx.loc['SSU', 1, 2, 2, 4],df_idx.loc['SSU', 1, 2, 3, 4])
# df_todraw = (df_idx.loc['SSU', 1, 2, 4, 9])
drawMultiPlots(df_todraw,['pixels','bright','humid','ec'], (18000,18000,18000,18000))
# drawMultiPlots(df_todraw,['pixels','bright','humid','ec'], (9000))
fig = plt.figure()


# df_sub = drawPlots(df,'bx','SSU',1,3,3,2,20000)
# df_sub = drawPlots(df,'bright','SSU',1,3,3,2,20000)
# %%

# %%
#%%
itv = '48H'
l = 0
exp_data = pd.concat([getStagedData(df_idx1.loc['SSU', 1, 3, 2, 3], interval=itv, lag=l),getStagedData(df_idx1.loc['SSU', 1, 3, 3, 3], interval=itv, lag=l),getStagedData(df_idx1.loc['SSU', 1, 2, 2, 4], interval=itv, lag=l),getStagedData(df_idx1.loc['SSU', 1, 2, 3, 4], interval=itv, lag=l)])
#%%
exp_data = pd.concat([exp_data,getStagedData(df_idx2.loc['SSU', 1, 3, 2, 2], interval=itv, lag=l),getStagedData(df_idx2.loc['SSU', 1, 3, 3, 2], interval=itv, lag=l),getStagedData(df_idx2.loc['SSU', 1, 2, 2, 4], interval=itv, lag=l),getStagedData(df_idx2.loc['SSU', 1, 2, 3, 4], interval=itv, lag=l)])
# exp_data = pd.concat([exp_data,getStagedData(df_idx3.loc['SSU', 1, 3, 2, 2]),getStagedData(df_idx3.loc['SSU', 1, 3, 3, 2]),getStagedData(df_idx3.loc['SSU', 1, 2, 1, 9]),getStagedData(df_idx3.loc['SSU', 1, 2, 4, 9])])
# exp_data = pd.concat([getStagedData(df_idx.loc['SSU', 1, 2, 2, 4]),getStagedData(df_idx.loc['SSU', 1, 2, 3, 4])])
#%%
exp_data = exp_data.dropna()
exp_data = exp_data[stats.zscore(exp_data['pct_pixels'])<2]
exp_data['bright_y*ec'] = exp_data['bright_y']*exp_data['ec']
exp_data['bright_y*temp_a'] = exp_data['bright_y']*exp_data['temp_a']
line_fitter = LinearRegression()
X=stats.zscore(exp_data[['pixels','bright_y','temp_a','ec','bright_y*temp_a']])
# X=stats.zscore(exp_data[['bright_y']])
y=exp_data['pct_pixels']
line_fitter.fit(X, y)
print(line_fitter.score(X,y))
# plt.scatter(exp_data['bright_x'], exp_data['pixels'])
# X= np.arange(0,15000,1)
plt.scatter(line_fitter.predict(X),y)
plt.plot(y,y)

# %%

# %%
fig, ax = plt.subplots(2,2)

ax[0,0].scatter(X['pixels'], y)
ax[0,1].scatter(X['temp_w'], y)
ax[1,0].scatter(X['temp_a'], y)
ax[1,1].scatter(X['ec'], y)




# %%
import statsmodels.api as sm
from statsmodels.formula.api import ols
exp_data['bright_b']=[exp_data['bright_y']>0]
model = ols('value ~ C(Genotype) + C(years) + C(Genotype):C(years)', data=exp_data).fit()
anova_table = sm.stats.anova_lm(model, typ=2)
# %%
