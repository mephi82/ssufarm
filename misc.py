from statistics import mean

def trc_mean(lraw, ratio = 0.1):
    l = [x for x in lraw if x is not None]#list(filter(None, lraw))
    l.sort()
    sindex = int(len(l)*(ratio))
    result = l[sindex:(len(l)-sindex)]
    # print(result)
    return(mean(result))