#%%
import mariadb, sys, datetime
import matplotlib.pyplot as plt 
import matplotlib.dates as md
import pandas as pd
from misc import trc_mean

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

def drawPlots(df, ylabel, site, rack, floor, pipe, pot, darkdrop=10000):
    df_idx = df.set_index(['site','rack','floor','pipe','pot'])
    subset = df_idx.loc[site, rack, floor, pipe, pot].copy()#.reset_index()
    
    subset = subset.loc[subset['bright']>darkdrop].copy()

    plt.plot(subset['timestamp'], subset[ylabel])

    ax = plt.gca()
    xfmt = md.DateFormatter('%d/%H')
    ax.xaxis.set_major_formatter(xfmt)
    # ax.set_xlim(min(df['timestamp']), max(df['timestamp']))
    # plt.xticks(rotation=25)
    plt.title(ylabel+':'+'/'.join(map(str,[rack, floor, pipe, pot])))
    plt.show()

# %%
# Get Cursor
conn = getConnDB()
df = getAggTable(conn, "2021-05-28 00:00:00", "2021-06-27 15:00:00", 1)
# drawPlots(df,'pixels','SSU',1,3,2,2)
conn.close()

# %%
# drawPlots(df,'bright','SSU',1,3,2,2)
drawPlots(df,'pixels','SSU',1,3,2,2,10000)
drawPlots(df,'bright','SSU',1,3,2,2,10000)

drawPlots(df,'pixels','SSU',1,3,3,2,10000)
drawPlots(df,'bright','SSU',1,3,3,2,10000)
# %%
