from statistics import mean

def trc_mean(l, ratio = 0.1):
    print(l)
    l.sort()
    sindex = int(len(l)*(ratio))
    result = l[sindex:(len(l)-sindex)]
    return(mean(result))