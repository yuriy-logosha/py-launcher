def str2SMH(val):
    arr = val.split(' ')
    return (int(arr[0]), int(arr[1]), int(arr[2]))


def build_result(_id, r, status):
    return {'type': 'result', 'id': _id, 'status': status, 'result': r}

def build_status(_id, r):
    return {'type': 'status', 'id': _id, 'status': r}


def row2List(row):
    lst = []
    [lst.append(row[i]) for i in range(4, len(row))]
    return lst

def to_time(time, datetime, processedTime, repeatInterval):
    if ':' in repeatInterval:
        d, m, y = (datetime.now().day, datetime.now().month, datetime.now().year)
        plan = time.strptime(str(y) + '-' + str(m) + '-' + str(d) + ' ' + repeatInterval, '%Y-%m-%d %H:%M')
        try:
            plan_tomorrow = time.strptime(str(y) + '-' + str(m) + '-' + str(d+1) + ' ' + repeatInterval, '%Y-%m-%d %H:%M')
        except ValueError as e:
            plan_tomorrow = time.strptime(str(y) + '-' + str(m+1) + '-1 ' + repeatInterval, '%Y-%m-%d %H:%M')
        return time.mktime(plan) - time.time() if time.mktime(plan) - time.time() >0 else time.mktime(plan_tomorrow) - time.time()
    else:
        sec, mins, hours = str2SMH(repeatInterval)
        next_time = processedTime + 60 * 60 * hours + 60 * mins + sec - time.time()
        return next_time if next_time > 0 else 0
