'''
2019_1108
最终版本

'''

import copy
import os
from collections import Counter
from xml.etree import ElementTree as ET
import json


import cv2 as cv
import numpy as np
import xlwt

BREAK_POINT_DIV_MAX2=1.15
BREAK_POINT_DIV_MIN2=0.85
BREAK_POINT_DIFF2 = 0.15
BREAK_POINT_DIV_MAX1=1.15
BREAK_POINT_DIV_MIN1=0.79
BREAK_POINT_DIFF1 = 0.15
BREAK_POINT_DIV_MAX3=1.18
BREAK_POINT_DIV_MIN3=0.79
BREAK_POINT_DIFF3 = 0.16
REGION = 0.45
FLOOR_ID = 'all'
INPUT_DATASET_NAME = 'Pred_result'
TRUE_OUTPUT_PATH = '/Users/zhuchenxi/PycharmProjects/row_test/result/{}_result/{}/true'.format(INPUT_DATASET_NAME,FLOOR_ID)
NEW_FALSE_OUTPUT_PATH = '/Users/zhuchenxi/PycharmProjects/row_test/result/{}_result/{}/false_new'.format(INPUT_DATASET_NAME,FLOOR_ID)
OLD_FALSE_OUTPUT_PATH = '/Users/zhuchenxi/PycharmProjects/row_test/result/{}_result/{}/false_old'.format(INPUT_DATASET_NAME,FLOOR_ID)
EXCEL_OUTPUT_PATH = '/Users/zhuchenxi/PycharmProjects/row_test/result/{}_result/{}'.format(INPUT_DATASET_NAME,FLOOR_ID)
INPUT_PATH = '/Users/zhuchenxi/PycharmProjects/row_test/dataset/{}/{}'.format(INPUT_DATASET_NAME,FLOOR_ID)
'''
划分3进行分区取计算点：
区域1 ：用左1/4中 坐标
区域2 ：用mid
区域3： 用右1/4中坐标
并且在3区域进行不同阈值的划分
'''
class DATA():
    def __init__(self):
        self.filename = None
        self.size = None
        self.object = {}
        self.object_name_dict={}
        self.coordinate = {}
        self.sorted_sku_name=[]
        self.sorted_slop_dict = {}
        self.div_each = []
        self.diff_each = []
        self.breakpoint_list = []
        self.group_dict = {}
        self.grid_dict = {}
        self.box_area = {}
        self.sqrt_dict = {}
        self.score_dict = []
        self.top3_list = []
        self.voting_score_threshold = 0.95

def read_xml(xml_dir,data):
    filename = xml_dir.split('/')[-1].strip('.xml')
    tree = ET.parse(xml_dir)
    root = tree.getroot()
    # filename = root.find('filename').text
    size = root.find('size')
    width = int(size.find('width').text)
    height = int(size.find('height').text)
    bndbox_list = []
    sku_list = []
    if  root.findall('object'):
        for object in root.findall('object'):
            bndbox = object.find('bndbox')
            xmin = int(bndbox.find('xmin').text)
            ymin = int(bndbox.find('ymin').text)
            xmax = int(bndbox.find('xmax').text)
            ymax = int(bndbox.find('ymax').text)
            sku = str(object.find('name').text)
            temp=[xmin,ymin,xmax,ymax]
            sku_list.append(sku)
            bndbox_list.append(temp)
            temp_dit1={}
            temp_name_dict = {}
        i = 0
        for sku,box in zip(sku_list,bndbox_list):
            if not (sku =='qb_unlabel'):
                # if sku =='518903fe-c4d0-11e9-ae8a-0242cb7ccd7c' :
                #     sku ='4efe649e-c4d0-11e9-9919-0242cb7ccd7c'
                temp_dit1[i]=box
                if sku not in temp_name_dict.keys():
                    temp_name_dict[sku] = [i]
                else:
                    temp_name_dict[sku].append(i)
                i +=1
        data.size=[width,height]
        data.object=copy.deepcopy(temp_dit1)
        data.filename = filename
        data.object_name_dict = copy.deepcopy(temp_name_dict)
        if i == 0 :
            return False
        else :
            return True
    else:
        data.size = [width, height]
        data.object = {}
        data.filename = filename
        data.object_name_dict = {}
        return False

def get_coordinate(data):
    temp_id = []
    temp_box = []
    for id,box in data.object.items():
        temp_box.append(box)
        temp_id.append(id)
    np_box = np.array(temp_box)
    coordinate_x = (np_box[:,2]+np_box[:,0])/2
    coordinate_y = (np_box[:,3]+np_box[:,1])/2
    temp_dict = {}
    area_dict = {}
    temp_list_area1 = []
    temp_list_area2 = []
    temp_list_area3 = []
    for b_x,b_y,id in zip(coordinate_x,coordinate_y,temp_id):
        for k, grid in data.grid_dict.items():
            x_min, y_min, x_max, y_max = grid
            if ((b_x>=x_min)and(b_y >= y_min)and(b_x<=x_max)and(b_y<=y_max)):
                if k == 1 :
                    final_x = (((temp_box[id][0] + temp_box[id][2]) / 2) + temp_box[id][0]) / 2
                    final_y = b_y
                if k == 2 :
                    final_x = (((temp_box[id][0]+temp_box[id][2])/2)+temp_box[id][0])/2
                    final_y  = b_y
                if k == 3:
                    final_x = (((temp_box[id][0] + temp_box[id][2]) / 2) + temp_box[id][0]) / 2
                    final_y = b_y
                if (k ==4 or k==5 or k == 6):
                    final_x = b_x
                    final_y = b_y
                if  k == 7 :
                    final_x = (((temp_box[id][2] + temp_box[id][0]) / 2) + temp_box[id][2]) / 2
                    final_y = b_y
                if k == 8:
                    final_x = (((temp_box[id][2]+temp_box[id][0])/2)+temp_box[id][2])/2
                    final_y = b_y
                if k == 9 :
                    final_x = (((temp_box[id][2] + temp_box[id][0]) / 2) + temp_box[id][2]) / 2
                    final_y = b_y
                temp_dict[id] = [final_x,final_y]
                if (k==1 or k==2 or k==3):
                    temp_list_area1.append(id)
                if (k==4 or k==5 or k==6):
                    temp_list_area2.append(id)
                if (k==7 or k==8 or k==9):
                    temp_list_area3.append(id)

    area_dict[1] = temp_list_area1
    area_dict[2] = temp_list_area2
    area_dict[3] = temp_list_area3
    data.box_area = copy.deepcopy(area_dict)
    data.coordinate = copy.deepcopy(temp_dict)

def get_slop(data):
    oirgin=np.array(data.size)/2
    temp_dict = {}
    sort_dict = {}
    sqrt_dict = {}
    sqrt_temp = {}
    for name,coordinate in data.coordinate.items():
        rx = oirgin[0]-coordinate[0]
        ry = oirgin[1]-coordinate[1]
        sqrt = np.sqrt(rx**2+ry**2)
        rmax = np.sqrt(oirgin[0]**2+oirgin[1]**2)
        slop = (oirgin[0]-coordinate[0])/(rmax-sqrt)
        temp_dict[name]= slop
        sqrt_temp[name] = sqrt
    sorted_sku_name = sorted(temp_dict, key=temp_dict.__getitem__)
    for k in sorted_sku_name :
        sort_dict[k] = temp_dict[k]
        sqrt_dict[k] = sqrt_temp[k]
    data.sorted_slop_dict = copy.deepcopy(sort_dict)
    data.sorted_sku_name = copy.deepcopy(sorted_sku_name)
    data.sqrt_dict = copy.deepcopy(sqrt_dict)

def get_div(data):
    div_list = []
    for i in range(1,len(data.sorted_sku_name)):
        sku_name_1 = data.sorted_sku_name[i-1]
        sku_name_2 = data.sorted_sku_name[i]
        div_each = data.sorted_slop_dict[sku_name_2]/data.sorted_slop_dict[sku_name_1]
        div_list.append(div_each)
    data.div_each = copy.deepcopy(div_list)

def get_diff(data):
    diff_list = []
    for i in range(1,len(data.sorted_sku_name)):
        sku_name_1 = data.sorted_sku_name[i-1]
        sku_name_2 = data.sorted_sku_name[i]
        div_each = data.sorted_slop_dict[sku_name_2]-data.sorted_slop_dict[sku_name_1]
        diff_list.append(div_each)
    diff_list.append(0)
    data.diff_each = copy.deepcopy(diff_list)

def judge(data):
    break_point = -1
    break_point_list = [0]
    for i in range(len(data.div_each)):
        if  data.sorted_sku_name[i] in data.box_area[2]:
            if (abs(data.div_each[i]>BREAK_POINT_DIV_MAX2) or abs(data.div_each[i]<BREAK_POINT_DIV_MIN2)) and (abs(data.diff_each[i])>BREAK_POINT_DIFF2):
                break_point = i+1
                break_point_list.append(break_point)
            else:
                if abs(data.diff_each[i])>BREAK_POINT_DIFF2:
                    min_dt = abs(data.div_each[i]-BREAK_POINT_DIV_MIN2)
                    max_dt = abs(data.div_each[i]-BREAK_POINT_DIV_MAX2)
                    diff2div = abs(data.diff_each[i]-BREAK_POINT_DIFF2) / BREAK_POINT_DIFF2
                    if max_dt>min_dt:
                        div_diff = BREAK_POINT_DIV_MIN2-(data.div_each[i] - diff2div)
                    else:
                        div_diff = data.div_each[i] + diff2div - BREAK_POINT_DIV_MAX2
                    if div_diff > REGION:
                        break_point = i + 1
                        break_point_list.append(break_point)
                if abs(data.div_each[i])> 4*BREAK_POINT_DIV_MAX2 and abs(data.diff_each[i])>0.5*BREAK_POINT_DIFF2:
                    break_point = i + 1
                    break_point_list.append(break_point)
                # elif (data.div_each[i]>BREAK_POINT_DIV_MAX2):
                #     dt =data.div_each[i] - BREAK_POINT_DIV_MAX2
                #     div2diff = dt*BREAK_POINT_DIFF2
                #     diff_div = data.diff_each[i] + div2diff
                #     if (abs(diff_div) > BREAK_POINT_DIFF2):
                #         break_point = i + 1
                #         break_point_list.append(break_point)
                # elif (data.div_each[i]<BREAK_POINT_DIV_MIN2):
                #     dt = BREAK_POINT_DIV_MIN2 - data.div_each[i]
                #     div2diff = dt * BREAK_POINT_DIFF2
                #     diff_div = data.diff_each[i] + div2diff
                #     if (abs(diff_div) > BREAK_POINT_DIFF2):
                #         break_point = i + 1
                #         break_point_list.append(break_point)

        if  data.sorted_sku_name[i] in data.box_area[1]:
            if (abs(data.div_each[i]>BREAK_POINT_DIV_MAX1) or abs(data.div_each[i]<BREAK_POINT_DIV_MIN1)) and (abs(data.diff_each[i])>BREAK_POINT_DIFF1):
                break_point = i+1
                break_point_list.append(break_point)
            else:
                if abs(data.diff_each[i])>BREAK_POINT_DIFF1:
                    min_dt = abs(data.div_each[i]-BREAK_POINT_DIV_MIN1)
                    max_dt = abs(data.div_each[i]-BREAK_POINT_DIV_MAX1)
                    diff2div = abs(data.diff_each[i]-BREAK_POINT_DIFF1) / BREAK_POINT_DIFF1
                    if max_dt>min_dt:
                        div_diff = BREAK_POINT_DIV_MIN1-(data.div_each[i] - diff2div)
                    else:
                        div_diff = data.div_each[i] + diff2div - BREAK_POINT_DIV_MAX1
                    if div_diff > REGION:
                        break_point = i + 1
                        break_point_list.append(break_point)

                # elif (data.div_each[i]>BREAK_POINT_DIV_MAX1):
                #     dt =data.div_each[i] - BREAK_POINT_DIV_MAX1
                #     div2diff = dt*BREAK_POINT_DIFF1
                #     diff_div = data.diff_each[i] + div2diff
                #     if (abs(diff_div) > BREAK_POINT_DIFF1):
                #         break_point = i + 1
                #         break_point_list.append(break_point)
                # elif (data.div_each[i]<BREAK_POINT_DIV_MIN1):
                #     dt = BREAK_POINT_DIV_MIN1 - data.div_each[i]
                #     div2diff = dt * BREAK_POINT_DIFF1
                #     diff_div = data.diff_each[i] + div2diff
                #     if (abs(diff_div) > BREAK_POINT_DIFF1):
                #         break_point = i + 1
                #         break_point_list.append(break_point)
        if  data.sorted_sku_name[i] in data.box_area[3]:
            if (abs(data.div_each[i]>BREAK_POINT_DIV_MAX3) or abs(data.div_each[i]<BREAK_POINT_DIV_MIN3)) and (abs(data.diff_each[i])>BREAK_POINT_DIFF3):
                break_point = i+1
                break_point_list.append(break_point)
            else:
                if abs(data.diff_each[i])>BREAK_POINT_DIFF3:
                    min_dt = abs(data.div_each[i]-BREAK_POINT_DIV_MIN3)
                    max_dt = abs(data.div_each[i]-BREAK_POINT_DIV_MAX3)
                    diff2div = abs(data.diff_each[i]-BREAK_POINT_DIFF3) / BREAK_POINT_DIFF3
                    if max_dt>min_dt:
                        div_diff = BREAK_POINT_DIV_MIN3-(data.div_each[i] - diff2div)
                    else:
                        div_diff = data.div_each[i] + diff2div - BREAK_POINT_DIV_MAX3
                    if div_diff > REGION:
                        break_point = i + 1
                        break_point_list.append(break_point)
                # elif (data.div_each[i]>BREAK_POINT_DIV_MAX3):
                #     dt =data.div_each[i] - BREAK_POINT_DIV_MAX3
                #     div2diff = dt*BREAK_POINT_DIFF3
                #     diff_div = data.diff_each[i] + div2diff
                #     if (abs(diff_div) > BREAK_POINT_DIFF3):
                #         break_point = i + 1
                #         break_point_list.append(break_point)
                # elif (data.div_each[i]<BREAK_POINT_DIV_MIN3):
                #     dt = BREAK_POINT_DIV_MIN3 - data.div_each[i]
                #     div2diff = dt * BREAK_POINT_DIFF3
                #     diff_div = data.diff_each[i] + div2diff
                #     if (abs(diff_div) > BREAK_POINT_DIFF3):
                #         break_point = i + 1
                #         break_point_list.append(break_point)
    break_point_list.append(len(data.div_each))
    data.breakpoint_list = copy.deepcopy(break_point_list)



def give_group_sku(data):
    temp_dict = {}
    for i in range(len(data.breakpoint_list)-1):
        start_point = data.breakpoint_list[i]
        end_point = data.breakpoint_list[i+1]
        if i==len(data.breakpoint_list)-2:
            temp_group = data.sorted_sku_name[start_point:end_point+1]
        else:
            temp_group = data.sorted_sku_name[start_point:end_point]
        temp_dict[i] = temp_group
    data.group_dict = copy.deepcopy(temp_dict)

def draw_group_box(data,output_path):
    name = data.filename+'.jpg'
    image_path = os.path.join(INPUT_PATH, name)
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    output_path = os.path.join(output_path, name)
    color_dict = {0: (0, 245, 255), 1: (0, 205, 102), 2: (132, 112, 255), 3: (255, 255, 0), 4: (178, 34, 34),
                  5: (148, 0, 211), 6: (255, 20, 147), 7: (222, 228, 0), 8: (229, 0, 29),9: (77, 0, 77)}
    image_data = cv.imread(image_path)
    print_div_each = data.div_each
    print_div_each.append(0)
    for i in range(len(data.sorted_sku_name)):
        xmin, ymin, xmax, ymax = data.object[i]
        for row,boxs in data.group_dict.items():
            if i in boxs:
                break
        cv.rectangle(image_data, (xmin, ymin), (xmax, ymax), color_dict[row], 3)  # 5代表线宽，
        text_name = str(data.sorted_sku_name.index(i))
        cv.putText(image_data, text_name, (xmin + 5, int(ymin - 1)), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,225), 2)
        cv.putText(image_data, str(round(data.sorted_slop_dict[data.sorted_sku_name.index(i)],3)), (xmin + 50, int(ymin - 1)), cv.FONT_HERSHEY_SIMPLEX, 1.0, (225, 0, 225), 2)
    cv.imwrite(output_path, image_data)

def auto_judge(data):
    count = 0
    # flag = False
    if len(data.group_dict) == len(data.object_name_dict):
        for row,output_group in data.group_dict.items():
            for sku,xml_group in data.object_name_dict.items():
                if set(output_group) == set(xml_group):
                    count+=1
        if count == len(data.object_name_dict):
            return True
        else:
            return False

    else:
        return False
def new_judge(data):
    i = 0
    for row, output_group in data.group_dict.items():
        temp_list = []
        for box_id in output_group:
            for sku,xml_box_id in data.object_name_dict.items():
                if box_id in xml_box_id:
                    temp_list.append(sku)
        temp_set = set(temp_list)
        if len(temp_set)==1:
            i+=1
    if len(data.group_dict)==i:
        return True
    else :
        return False




def make_grid(data):
    anchor_X,anchor_Y = data.size
    step_x,step_y = anchor_X/3,anchor_Y/3
    i = 1
    temp_grid_dict = {}
    for rank_id in range(1,4):
        rank_min = step_x*(rank_id-1)
        rank_max = step_x*rank_id
        for row_id in range(1,4):
            row_max = row_id*step_y
            row_min = (row_id-1)*step_y
            temp_grid_dict[i] = (rank_min,row_min,rank_max,row_max)
            i+=1
    data.grid_dict = temp_grid_dict

def make_excel(data,output_path):
    file = xlwt.Workbook(encoding='utf-8')
    # 创建一个名为data的表单
    table = file.add_sheet('data', cell_overwrite_ok=True)
    # 表头信息
    table_head = ['box_id','sku_name','x_mid','y_mid','sqrt', '1/slope', 'div_each', 'diff_each', 'area_id', 'row_id']
    # 将表头信息写入到表格的第一行
    for i in range(len(table_head)):
        table.write(0, i, table_head[i])
    for i in range(0,len(data.sorted_sku_name)):
        box_id = data.sorted_sku_name[i]
        k = i+1
        l = data.sorted_sku_name.index(box_id)
        table.write(k,0,l)
        for name,box in data.object_name_dict.items():
            if box_id in box:
                table.write(k, 1,str(name))
                break
        x_mid,y_mid = data.coordinate[box_id]
        table.write(k, 2, x_mid)
        table.write(k, 3, y_mid)
        table.write(k,4,data.sqrt_dict[box_id])
        table.write(k, 5, data.sorted_slop_dict[box_id])
        table.write(k,6,data.div_each[i])
        table.write(k, 7, data.diff_each[i])
        for area,box in data.box_area.items():
            if box_id in box:
                table.write(k, 8,area)
                break
        for group,box in data.group_dict.items():
            if box_id in box:
                table.write(k, 9,group)
                break
    name = data.filename + '.xls'
    # name = 'error.xls'
    output_path = os.path.join(output_path, name)
    file.save(output_path)

def final_excel_result(correct,correct1,error,error1):
    total = error + correct
    error_rate_new = error / total
    total1 = error1 + correct1
    error_rate_old = error1 / total1
    print('new correct is %d' % correct)
    print('new error is %d' % error)
    print('new judge error rate is %4f' % error_rate_new)
    print('new correct vs old error rate is %4f' % error_rate_old)
    file = xlwt.Workbook(encoding='utf-8')
    # 创建一个名为data的表单
    table = file.add_sheet('RESULET', cell_overwrite_ok=True)
    # 表头信息
    table_head = ['DATA_SET_NAME', 'FLOOR_ID', 'NEW_CORRECT_NUM', 'NEW_EORROR_NUM', 'NEW_JUDGE_ERROR_RATE', 'NEW_CORRECT_VS_OLD_ERROR_RATE']
    # 将表头信息写入到表格的第一行
    for i in range(len(table_head)):
        table.write(0, i, table_head[i])
    table.write(1, 0, INPUT_DATASET_NAME)
    table.write(1, 1, FLOOR_ID)
    table.write(1, 2, correct)
    table.write(1, 3, error)
    table.write(1, 4, error_rate_new)
    table.write(1, 5, error_rate_old)
    name = INPUT_DATASET_NAME+'_'+str(FLOOR_ID) + '.xls'
    output_path = os.path.join(EXCEL_OUTPUT_PATH, name)
    file.save(output_path)

def voting_system(data):
    flag_3 = False
    flag_2 = False
    for trace,box_list in data.group_dict.items():
        temp_list = []
        if len(box_list) > 2 and len(box_list)<8:
            for box_id in box_list:
                for sku_name,box_list2 in data.object_name_dict.items():
                    if box_id in box_list2:
                        temp_list.append(sku_name)
                        break
            if len(temp_list)>0 :
                result = Counter(temp_list)
            else:
                result = {}
            for sku_name2,number in result.items():
                if number >= (len(box_list))/2.0:
                    vale_lsit = list(result.values())
                    temp_dict = {}
                    if len(vale_lsit)==2 and vale_lsit[0]==vale_lsit[1]:
                        for b_id in box_list:
                            for sk,v in data.object_name_dict.items():
                                if b_id in v:
                                    temp_dict[b_id] = sk
                                    break
                        temp_list1=[]
                        temp_list2=[]
                        box_group = list(temp_dict.keys())
                        sku_group = list(set(temp_dict.values()))
                        for b_id,group in temp_dict.items():
                            if group == sku_group[0]:
                                temp_list1.append(data.score_dict[b_id])
                            else:
                                temp_list2.append(data.score_dict[b_id])
                        mean_1 = np.array(temp_list1).mean()
                        mean_2 = np.array(temp_list2).mean()
                        if mean_1 > mean_2+0.1:
                            final_sku_name = sku_group[0]
                        elif mean_2 > mean_1+0.1:
                            final_sku_name = sku_group[1]
                        else:
                            break

                    else:
                        final_sku_name = sku_name2
                    for box_id in box_list:
                        for sku_name, box_list2 in data.object_name_dict.items():
                            if box_id in box_list2:
                                if sku_name != final_sku_name and data.score_dict[box_id]<data.voting_score_threshold:# and final_sku_name in data.top3_list[box_id] :
                                    data.object_name_dict[final_sku_name].append(box_id)
                                    data.object_name_dict[sku_name].remove(box_id)
                                    flag_3 = True
        if len(box_list) == 2:
            if data.score_dict[box_list[0]] < 0.8 or data.score_dict[box_list[1]] < 0.8:
                if data.score_dict[box_list[0]]<0.8 and data.score_dict[box_list[1]]> 0.8:
                    for sku,id in data.object_name_dict.items():
                        if box_list[1] in id :
                            final_sku_name = sku
                            break
                    for box_id in box_list:
                        for sku_name, box_list2 in data.object_name_dict.items():
                            if box_id in box_list2:
                                if sku_name != final_sku_name and data.score_dict[box_id]<0.8 and final_sku_name in data.top3_list[box_id] :
                                    data.object_name_dict[final_sku_name].append(box_id)
                                    data.object_name_dict[sku_name].remove(box_id)
                                    flag_2 = True
                elif data.score_dict[box_list[0]]>0.8 and data.score_dict[box_list[1]] < 0.8:
                    for sku,id in data.object_name_dict.items():
                        if box_list[0] in id :
                            final_sku_name = sku
                            break
                    for box_id in box_list:
                        for sku_name, box_list2 in data.object_name_dict.items():
                            if box_id in box_list2:
                                if sku_name != final_sku_name and data.score_dict[box_id]<0.8 and final_sku_name in data.top3_list[box_id] :
                                    data.object_name_dict[final_sku_name].append(box_id)
                                    data.object_name_dict[sku_name].remove(box_id)
                                    flag_2 = True
                else:
                    pass
    temp_list = []
    for sku_name,box_list in data.object_name_dict.items():
        if len(box_list) == 0:
            temp_list.append(sku_name)
    for del_member in temp_list:
        data.object_name_dict.pop(del_member)
    return flag_3,flag_2

def get_data_from_array(data,classes,class_score,origin_boxes,top3_list):
    data.size = [1280, 960]
    float_to_int = (1280, 960, 1280, 960)
    origin_boxes[:,[0,1]] = origin_boxes[:,[1,0]]
    origin_boxes[:, [2, 3]] = origin_boxes[:, [3, 2]]
    data.score_dict = class_score

    real_box = list(np.array(origin_boxes *float_to_int, dtype='int32'))
    temp_dit1 = {}
    i=0
    temp_name_dict = {}
    for sku,box in zip(classes,real_box):
        temp_dit1[i] = list(box)
        if sku not in temp_name_dict.keys():
            temp_name_dict[sku] = [i]
        else:
            temp_name_dict[sku].append(i)
        i += 1
    data.object = copy.deepcopy(temp_dit1)
    data.object_name_dict = copy.deepcopy(temp_name_dict)
    data.top3_list = top3_list



def voting(classes,class_score,origin_boxes,top3_list,output_xml=None):
    if  len(origin_boxes)>0:
        data = DATA()
        get_data_from_array(data,classes,class_score,origin_boxes,top3_list)
        make_grid(data)
        get_coordinate(data)
        get_slop(data)
        get_div(data)
        get_diff(data)
        judge(data)
        give_group_sku(data)
        if output_xml !=None:
            save_xml(data,output_xml)
        # data.div_each.append(0)
        # make_excel(data, '/Users/zhuchenxi/PycharmProjects/my_inf/meidi_inference/error_path')
        # print(data.object_name_dict)
        voting_flag_3,voting_flag_2 = voting_system(data)
        # print(data.object_name_dict)
        new_classes = np.zeros(len(classes),dtype='int32')
        for sku,id_list in data.object_name_dict.items():
            for id in id_list:
                new_classes[id] = sku
        return new_classes,voting_flag_3,voting_flag_2
    else:
        return classes,False,False

def save_xml(data,output_xml):
    XML_OUT = 'xml_output'
    if not os.path.exists(XML_OUT):
        os.makedirs(XML_OUT)
    out0 = '''<?xml version="1.0" encoding="utf-8"?>
    <annotation>
    	<folder>None</folder>
    	<filename>%(name)s</filename>
    	<source>
    		<database>None</database>
    		<annotation>None</annotation>
    		<image>None</image>
    		<flickrid>None</flickrid>
    	</source>
    	<owner>
    		<flickrid>None</flickrid>
    		<name>None</name>
    	</owner>
    	<segmented>0</segmented>
    	<size>
    		<width>%(width)d</width>
    		<height>%(height)d</height>
    		<depth>3</depth>
    	</size>
    '''
    out1 = '''	<object>
    		<name>%(class)s</name>
            <pose>Unspecified</pose>
    		<truncated>0</truncated>
    		<difficult>0</difficult>
    		<bndbox>
    			<xmin>%(xmin)d</xmin>
    			<ymin>%(ymin)d</ymin>
    			<xmax>%(xmax)d</xmax>
    			<ymax>%(ymax)d</ymax>
    		</bndbox>
    	</object>
    '''
    out2 = '''</annotation>'''
    source = {}
    label = {}
    source['name'] = output_xml.split('.')[0]+'.jpg'
    source['width'] = 1280
    source['height'] = 960
    fxml = os.path.join(XML_OUT,output_xml)
    fxml = open(fxml, 'w')
    fxml.write(out0 % source)
    for i in range(len(data.object)):
        for sku, box_id_list in data.group_dict.items():
            if i in box_id_list:
                sku_name = sku
                break
        uuid_dict = json.load(open('./Meadi_1118.map'))
        for uuid, sku in uuid_dict.items():
            if sku_name == sku:
                final_uuid = uuid
                break
        label['class'] = final_uuid
        label['xmin'] = data.object[i][0]
        label['ymin'] = data.object[i][1]
        label['xmax'] = data.object[i][2]
        label['ymax'] = data.object[i][3]
        fxml.write(out1 % label)
    fxml.write(out2)








if __name__ == '__main__':
    data_dir = INPUT_PATH
    filenames = os.listdir(data_dir)
    data = DATA()
    error = 0
    correct = 0
    correct1 = 0
    error1 = 0
    for filename in filenames:
        if filename.endswith('xml'):
            print(filename)
            xml_dir = os.path.join(data_dir,filename)
            flag=read_xml(xml_dir,data)
            if flag :
                make_grid(data)
                get_coordinate(data)
                get_slop(data)
                get_div(data)
                get_diff(data)
                judge(data)
                give_group_sku(data)
                voting_system(data)
                flag_old=auto_judge(data)
                flag_new = new_judge(data)
                if flag_new:
                    correct+=1
                    if flag_old:
                        correct1+=1
                        # draw_group_box(data,TRUE_OUTPUT_PATH)
                    else:
                        draw_group_box(data, OLD_FALSE_OUTPUT_PATH)
                        error1 += 1
                        make_excel(data, OLD_FALSE_OUTPUT_PATH)

                else:
                    draw_group_box(data,NEW_FALSE_OUTPUT_PATH)
                    error+=1
                    make_excel(data, NEW_FALSE_OUTPUT_PATH)
            else:
                continue
    final_excel_result(correct,correct1,error,error1)
    # total = error+correct
    # error_rate_new = error/total
    # total1 = error1+correct1
    # error_rate_old = error1/total1
    # print('new correct is %d' % correct)
    # print('new error is %d' % error)
    # print('new judge error rate is %4f'  %error_rate_new)
    # print('new correct vs old error rate is %4f' % error_rate_old)