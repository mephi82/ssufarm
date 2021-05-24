from statistics import mean

def trc_mean(lraw, ratio = 0.1):
    l = list(filter(None, lraw))
    l.sort()
    sindex = int(len(l)*(ratio))
    result = l[sindex:(len(l)-sindex)]
    return(mean(result))