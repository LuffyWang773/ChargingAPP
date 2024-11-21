# -*- coding: utf-8 -*-
"""
Created on Tue Aug 20 09:00:22 2024

@author: Wang Luffy
"""
# from streamlit import *
import streamlit as st
import numpy as np
import pandas as pd
from datetime import time,datetime,timedelta
import copy
# from streamlit_echarts import st_pyecharts
from streamlit_echarts import st_echarts
# import datetime

def charge_Limitedphase3(clockTime,SOC_state,resPower_Transformer,charged_power,clockLength,powerVolume,Battery):
    '''
    电池功率受限状态下计算充电功率、时间，更新电池状态
    clockTime,电池时钟当前时间
    SOC_state,电池当前SOC状态
    resPower_Transformer,变压器可提供功率（当前能提供的最大功率）
    charged_power,已充电电量（已经历阶段的所有电量）
    '''
    if SOC_state == 1:
        #第一阶段       #下一块电池需求功率,当前阶段 剩余功率 和 需求功率 取小    
        if clockTime < Battery.t1 :  #计算时间时向上取整, 最小单位为min, 
            curPower_Battery_n,SOC_state = min(resPower_Transformer, Battery.P1), 1 
            clockTime  +=1
            charged_power += curPower_Battery_n
        else:
            curPower_Battery_n,SOC_state = min(resPower_Transformer, Battery.P2), 2  
            clockTime  +=1
            charged_power += curPower_Battery_n
    elif SOC_state == 2:
        #第二阶段                                       ###   or 还是 and ？
        if clockTime < (Battery.t1+Battery.t2) or charged_power < (Battery.t2*Battery.P2):
            curPower_Battery_n,SOC_state = min(resPower_Transformer, Battery.P2), 2 
            clockTime  +=1
            charged_power += curPower_Battery_n
        else:
            curPower_Battery_n,SOC_state = min(resPower_Transformer, Battery.P3), 3  
            clockTime  +=1
            charged_power += curPower_Battery_n
    elif SOC_state == 3:
        #第三阶段     
        if clockTime < (Battery.t1+Battery.t2+Battery.t3)  or charged_power < (Battery.t2*Battery.P2+Battery.t3*Battery.P3):
            curPower_Battery_n,SOC_state = min(resPower_Transformer, Battery.P3), 3 
            clockTime  +=1
            charged_power += curPower_Battery_n
        else:
            curPower_Battery_n,SOC_state = min(resPower_Transformer, Battery.P4), 4 
            clockTime  +=1
            charged_power += curPower_Battery_n
    elif SOC_state == 4:
        #第四阶段      
        if clockTime < (clockLength - Battery.t5 - Battery.t6) or charged_power < (powerVolume - Battery.t6*Battery.P6 - Battery.t5*Battery.P5):
            curPower_Battery_n,SOC_state = min(resPower_Transformer, Battery.P4), 4 
            clockTime  +=1
            charged_power += curPower_Battery_n
        else:
            curPower_Battery_n,SOC_state = min(resPower_Transformer, Battery.P5), 5 
            clockTime  +=1
            charged_power += curPower_Battery_n
    elif SOC_state == 5:     # powerVolume
        #第五阶段
        if clockTime < (clockLength - Battery.t6) or charged_power < (powerVolume - Battery.t6*Battery.P6):
            curPower_Battery_n,SOC_state = min(resPower_Transformer, Battery.P5), 5 
            clockTime  +=1
            charged_power += curPower_Battery_n
        else:
            curPower_Battery_n,SOC_state = min(resPower_Transformer, Battery.P6), 6 
            clockTime  +=1
            charged_power += curPower_Battery_n
    else:    # SOC_state == 6
        #第六阶段     
        if clockTime < clockLength  or charged_power < powerVolume:
            curPower_Battery_n,SOC_state = min(resPower_Transformer, Battery.P6), 6 
            clockTime  +=1
            charged_power += curPower_Battery_n
        else:
            curPower_Battery_n,SOC_state = Battery.P1, 1
            clockTime  = 0
            charged_power = 0
#            num_chargedBattery += 1
    return curPower_Battery_n, SOC_state, clockTime, charged_power 

class battery():  #定义电池充电阶段    
    def __init__(self, t1,t2,t3,t4,t5,t6, P1,P2,P3,P4,P5,P6): #外部传参，赋予属性  
        self.t1, self.t2, self.t3, self.t4, self.t5, self.t6 = t1,t2,t3,t4,t5,t6
        self.P1, self.P2, self.P3, self.P4, self.P5, self.P6 = P1,P2,P3,P4,P5,P6

#####################################前端页面#################################
# 设置页面标题
# st.title('CTB400电池服务能力测算')
st.set_page_config(page_title="服务能力测算平台", page_icon=":articulated lorry:",initial_sidebar_state="auto")

tolPower_Transformer0 = st.sidebar.number_input("变压器总功率",value = 1250, step = 1)
Conversion_coeff = st.sidebar.number_input("功率因数",value = 0.95, step = 0.01)
tolPower_Transformer = st.sidebar.number_input("视在功率",value = int(tolPower_Transformer0*Conversion_coeff))
maxNum_Battery = st.sidebar.number_input("电池数量",value = 4, min_value = 2, step = 1)

#输入充电时长
time_length = st.sidebar.slider('时间区间', value=(time(0, 0), time(12, 0)))
# 将时间转换为timedelta对象  # 将timedelta列转换为Timedelta类型
start_time = timedelta(hours=time_length[0].hour, minutes=time_length[0].minute, seconds=time_length[0].second)
end_time   = timedelta(hours=time_length[1].hour, minutes=time_length[1].minute, seconds=time_length[1].second)
# st.write("时间差:", (end_time - start_time).seconds/60)  #转换为分钟数
ChargingTime_interval = int((end_time - start_time).seconds/60)  # = 360 * 4  单位min，默认从0点计时

#电池状态参数
num_P1 = st.sidebar.number_input("SOC00功率",value = 0)
num_T1 = st.sidebar.number_input("SOC00时长",value = 3)
num_P2 = st.sidebar.number_input("SOC01功率",value = 0)
num_T2 = st.sidebar.number_input("SOC02时长",value = 3)
num_P3 = st.sidebar.number_input("SOC1功率",value = 320)
num_T3 = st.sidebar.number_input("SOC1时长",value = 53)
num_P4 = st.sidebar.number_input("SOC2功率",value = 225)
num_T4 = st.sidebar.number_input("SOC2时长",value = 6)
num_P5 = st.sidebar.number_input("SOC3功率",value = 140)
num_T5 = st.sidebar.number_input("SOC3时长",value = 6)
num_P6 = st.sidebar.number_input("SOC4功率",value = 105)
num_T6 = st.sidebar.number_input("SOC4时长",value = 5)

#################后台算法#################################
# global df_Charging
# global num_chargedBattery
# num_chargedBattery = 0
df_Charging = pd.DataFrame(columns=['curTime','load_T', 'loadRatio_T'])
# 初始化 State 对象
state1 = st.empty()  # num_chargedBattery
state2 = st.empty()  # df_Charging

@st.cache_data    #缓存装饰器
def Charging(ChargingTime_interval,tolPower_Transformer,maxNum_Battery,df_Charging,num_T1,num_T2,num_T3,num_T4,num_T5,num_T6,num_P1,num_P2,num_P3,num_P4,num_P5,num_P6):

    # global df_Charging
    # global num_chargedBattery
    df_Charging = df_Charging.drop(df_Charging.index, inplace=False) #内容清空, 创建并返回新的对象  inplace = False

    #切换电池型号
    # add_selectbox = st.sidebar.selectbox( 
    Battery = battery(num_T1-1,num_T2, num_T3, num_T4, num_T5, num_T6,
                      num_P1,  num_P2, num_P3, num_P4, num_P5, num_P6)  #CTB284电池
    clockLength = sum([Battery.t1, Battery.t2, Battery.t3, Battery.t4, Battery.t5, Battery.t6 ])
    powerVolume = sum([Battery.t1*Battery.P1, Battery.t2*Battery.P2, Battery.t3*Battery.P3, Battery.t4*Battery.P4, Battery.t5*Battery.P5, Battery.t6*Battery.P6 ])
    Battery_seed = {'SOC': 1, 'Positive_Clock': 0, 'charged_power':0}  #单块电池的身份证，SOC状态、单块电池时钟时间,单块电池已充电量

    ##定义电池仓,设置电池初始状态
    names = locals()
    for i in range(maxNum_Battery):   
        names['Battery' + str(i) ] = copy.deepcopy(Battery_seed)
        names['curPower_Battery' + str(i)],names['Battery' + str(i)]['SOC'],names['Battery' + str(i)]['charged_power'] = 0, 1, 0 

    num_chargedBattery = 0 #已充电电池数量, 服务能力
    curNum_Battery = 0 #电池仓中当前电池数量
    curTime = 0  #全局时间
    for curTime in range(ChargingTime_interval-1):      #未到总时长限制,逐分钟刷新电池充电状态
        #初始换电条件：充电仓内满电电池未替换一轮，只有一个换电机器人（间隔6分钟）
        if curTime%(1 + Battery.t1 + Battery.t2) == 0:  #每6分钟执行一次换电动作
            curNum_Battery +=1  #新增一块电池
            if curNum_Battery <= maxNum_Battery:
                num_chargedBattery += 1 #首先替换所有的满电电池
                # print('curTime{}，当前电池数{}，服务能力{}'.format(curTime,curNum_Battery, num_chargedBattery))   
            
        if curNum_Battery <= maxNum_Battery:
            curPower_BatteryList = []
            for num in range(curNum_Battery):       
                curPower_BatteryList.append(names['curPower_Battery' + str(num)])
            curPower_BatteryArray = np.array(curPower_BatteryList)
            
            #更新每块电池的充电状态,判断功率是否受限 
            for i in range(curNum_Battery):                             
                if names['Battery' + str(i)]['Positive_Clock'] < clockLength  or names['Battery' + str(i)]['charged_power'] < powerVolume:
        #            resPower_Transformer 变压器剩余功率 = 变压器总功率 - 电池仓中当前电池充电总功率
                    resPower_Transformer = tolPower_Transformer - sum(np.delete(curPower_BatteryArray, i))    
        
                    if resPower_Transformer > 0:    #有剩余功率
                        names['curPower_Battery' + str(i)], names['Battery' + str(i)]['SOC'], names['Battery' + str(i)]['Positive_Clock'], names['Battery' + str(i)]['charged_power'] = charge_Limitedphase3(names['Battery' + str(i)]['Positive_Clock'],names['Battery' + str(i)]['SOC'],resPower_Transformer,names['Battery' + str(i)]['charged_power'],clockLength,powerVolume,Battery)
                    else:                           #无剩余功率
                        names['curPower_Battery' + str(i)], names['Battery' + str(i)]['SOC'], names['Battery' + str(i)]['Positive_Clock'], names['Battery' + str(i)]['charged_power'] = 0, names['Battery' + str(i)]['SOC'],names['Battery' + str(i)]['Positive_Clock'], names['Battery' + str(i)]['charged_power']
                else:                               #电池充满电，服务能力加一，状态重置
                    names['curPower_Battery' + str(i)], names['Battery' + str(i)]['SOC'], names['Battery' + str(i)]['Positive_Clock'], names['Battery' + str(i)]['charged_power'] = Battery.P1, 1, 0, 0
                    num_chargedBattery += 1
                curPower_BatteryArray[i] = names['curPower_Battery' + str(i)] # 功率更新
                
        else:  # 初始满电电池替换完毕后正常刷新          
            curPower_BatteryList = []  #[0]* maxNum_Battery
            #汇总所有电池的充电功率，方便计算变压器剩余功率
            for num in range(maxNum_Battery):       
                curPower_BatteryList.append(names['curPower_Battery' + str(num)])
            curPower_BatteryArray = np.array(curPower_BatteryList)
            
            #更新每块电池的充电状态,判断功率是否受限 
            for i in range(maxNum_Battery):                             
                if names['Battery' + str(i)]['Positive_Clock'] < clockLength  or names['Battery' + str(i)]['charged_power'] < powerVolume:
        #            resPower_Transformer 变压器剩余功率 = 变压器总功率 - 电池仓中当前电池充电总功率
                    resPower_Transformer = tolPower_Transformer - sum(np.delete(curPower_BatteryArray, i))    
        
                    if resPower_Transformer > 0:    #有剩余功率
                        names['curPower_Battery' + str(i)], names['Battery' + str(i)]['SOC'], names['Battery' + str(i)]['Positive_Clock'], names['Battery' + str(i)]['charged_power'] = charge_Limitedphase3(names['Battery' + str(i)]['Positive_Clock'],names['Battery' + str(i)]['SOC'],resPower_Transformer,names['Battery' + str(i)]['charged_power'],clockLength,powerVolume,Battery)
                    else:                           #无剩余功率
                        names['curPower_Battery' + str(i)], names['Battery' + str(i)]['SOC'], names['Battery' + str(i)]['Positive_Clock'], names['Battery' + str(i)]['charged_power'] = 0, names['Battery' + str(i)]['SOC'],names['Battery' + str(i)]['Positive_Clock'], names['Battery' + str(i)]['charged_power']
                else:                               #电池充满电，服务能力加一，状态重置
                    names['curPower_Battery' + str(i)], names['Battery' + str(i)]['SOC'], names['Battery' + str(i)]['Positive_Clock'], names['Battery' + str(i)]['charged_power'] = Battery.P1, 1, 0, 0
                    num_chargedBattery += 1
                curPower_BatteryArray[i] = names['curPower_Battery' + str(i)] # 功率更新
            
        #计算所有电池当前占用的总功率
        curPower_ChargingBattery = 0        
        for i in range(maxNum_Battery):
            curPower_ChargingBattery += names['curPower_Battery' + str(i)]
        
        load_Transformer, loadRatio_Transformer = curPower_ChargingBattery, curPower_ChargingBattery/tolPower_Transformer
        line = pd.Series({'curTime':curTime,
                        'load_T':load_Transformer,'loadRatio_T':loadRatio_Transformer,
                        'num_chargedBattery':num_chargedBattery})
        for i in range(maxNum_Battery):
            line.loc['B{}_Power'.format(i+1)] = names['curPower_Battery' + str(i)]
            line.loc['B{}_SOC'.format(i+1)] = names['Battery' + str(i)]['SOC']
            line.loc['B{}_chargedPower'.format(i+1)] = names['Battery' + str(i)]['charged_power']

        df_Charging = df_Charging._append(line, ignore_index=True)
        # print('当前时间：{}，功率：{}'.format(curTime, curPower_ChargingBattery))

    print('>>>>>>>>  服务能力：{}    <<<<<<<<<'.format(num_chargedBattery))
    df_Charging2 = pd.DataFrame(columns = df_Charging.columns)
    df_Charging2.loc[0] = df_Charging.loc[0]  # 复制df1中的第一行到df2中
    df_Charging = pd.concat([df_Charging2,df_Charging], axis=0 ,ignore_index=True) #参数axis=0表示上下合并
    # df_Charging.to_csv('./Charging.csv',sep=',',index=False,header=True)        
    df_Charging.to_csv('./Running log/Charging-T{}-B{}-S{}.csv'.format(tolPower_Transformer,maxNum_Battery,num_chargedBattery),sep=',',index=False,header=True) 

    load_Transformer, loadRatio_Transformer = df_Charging.loc[:,"load_T"],df_Charging.loc[:,"loadRatio_T"]
    #x_list = [x * x for x in range(ChargingTime_interval)]

    state1.value = num_chargedBattery
    # state2.value = df_Charging
    return num_chargedBattery,df_Charging

##############前端输出#################################
if st.button('计算服务能力'):
    num_chargedBattery,df_Charging = Charging(ChargingTime_interval,tolPower_Transformer,maxNum_Battery,df_Charging,num_T1,num_T2,num_T3,num_T4,num_T5,num_T6,num_P1,num_P2,num_P3,num_P4,num_P5,num_P6)
    st.write("服务能力:{}块".format(num_chargedBattery))

load_Transformer, loadRatio_Transformer = df_Charging.loc[:,"load_T"],df_Charging.loc[:,"loadRatio_T"]
#x_list = [x * x for x in range(ChargingTime_interval)]

format = "%H:%M:%S"
datetime_1 = datetime.strptime(str(start_time), format)
datetime_2 = datetime.strptime(str(end_time), format)
index_time = pd.date_range(datetime_1,datetime_2,freq='1min').tolist()

loadRatio_Transformer2 = loadRatio_Transformer.tolist()
def conv_str(x):
    return str(x)[11:16]
index_time2 = list(map(conv_str, index_time))

options = {
    "title": {"text": "变压器负荷率曲线"},
    "tooltip": {"trigger": "axis"},
    "legend": {"data": ["负荷率"]},
    "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
    "toolbox": {"feature": {"saveAsImage": {}}},
    "xAxis": {
        "type": "category",
        "boundaryGap": False,
        "data": index_time2,
    },
    "yAxis": {"type": "value"},
    "series": [
        {
            "name": "负荷率",
            "type": "line",
            "stack": "总量",
            "data": loadRatio_Transformer2,
        },
    ],
}
st_echarts(options=options)


st.write("运行记录：")
if st.checkbox('Show dataframe'):   #使用复选框显示/隐藏数据
    st.dataframe(df_Charging)

