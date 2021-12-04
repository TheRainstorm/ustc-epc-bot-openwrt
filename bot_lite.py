import requests
import json
import re
import time
import os
import sys
from lxml import etree
from noftify import EmailSender

class Bot():
    URL_ROOT     = "http://epc.ustc.edu.cn/"
    URL_LOGIN    = URL_ROOT + "n_left.asp"
    URL_BOOKED   = URL_ROOT + "record_book.asp"
    URL_BOOKABLE = {
        "situational"   : URL_ROOT + "m_practice.asp?second_id=2001",   #Situational Dialogue
        "topic"       : URL_ROOT + "m_practice.asp?second_id=2002",   #Topical Discussion
        "debate"        : URL_ROOT + "m_practice.asp?second_id=2003",   #Debate
        "drama"         : URL_ROOT + "m_practice.asp?second_id=2004",   #Drama
        "pronunciation" : URL_ROOT + "m_practice.asp?second_id=2007",   #Pronunciation Practice
    }

    def __init__(self, config, filter_week=None, have_email=False, silent=False, force_send_email=False):
        self.ustc_id     = config["ustc_id"]
        self.ustc_pwd    = config["ustc_pwd"]
        self.wday_perfer = config["wday_perfer"]

        self.no_offline_course = config["no_offline_course"]

        if filter_week is None:    #如果没有指定星期，则默认为全部星期
            self.filter_week = [i for i in range(1,21)]
        else:
            self.filter_week = filter_week

        self.booked_score = 0
        self.max_book_score = 8

        self.new_booked_course_json_file = os.path.join(sys.path[0], 'course_to_cancel.json')          #保存已预约的课程
        self.sorted_released_course_json_file = os.path.join(sys.path[0], 'course_to_submit.json')     #保存可预约的课程

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
                AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.75 Safari/537.36"
        })

        self.silent = silent    #是否静默模式（命令行不输出INFO信息）

        self.have_email = have_email                #表示是否设置了邮件（地址，授权码等），未设置时邮件相关代码不执行
        self.force_send_email = force_send_email    #自动模式有课可选时才会发邮件，该选项用于强制发送邮件
        if self.have_email:
            self.email_sender = EmailSender(
                    config['email_rcv_addr'],
                    config['email_send_addr'],
                    config['email_smtp_addr'],
                    config['email_auth_code']
                )
        
        self.login()

    def run(self):
        '''
        运行默认策略
        1. 先获得发布的课程列表
        2. 按照优先级排序
        3. 尝试直接预约可预约课程
        4. 发送邮件通知发布的课程，以及已预约的课程
        '''
        #查看已选课程，new_booked表示预约了没上的课程
        self.print_log(0, "Getting booked course list...")
        booked_hour, new_booked_hour, new_booked_course_list, _ = self.get_booked_course()
        self.print_log(0, "已预约学时: %d, 新预约学时: %d" %(booked_hour, new_booked_hour))
        self.dump_course_list(self.new_booked_course_json_file, new_booked_course_list)
        self.booked_score = new_booked_hour

        #获得发布的课程列表
        self.print_log(0, "Getting released course list...")
        course_dict_list = self.get_released_course(select='topic')
        if len(course_dict_list) == 0:
            self.print_log(0, "No released course, exit")
            exit(0)
        
        #对课程按照优先级排序
        self.print_log(0, "Sorting course...")
        course_dict_list = self.add_priority(course_dict_list)  #为每个course_dict添加优先级属性，方便人工选择
        course_dict_list_sorted = self.sort_by_priority(course_dict_list)
        self.dump_course_list(self.sorted_released_course_json_file, course_dict_list_sorted)

        #打印可预约的课程
        self.print_log(0, "Released course list:")
        self.print_released_course_list(course_dict_list_sorted)

        #尝试直接提交可预约课程
        self.print_log(0, "Trying to book released course...")
        try_count = self.try_submit_course(course_dict_list_sorted, new_booked_course_list)
        if try_count==0:
            self.print_log(2, "No released course can be booked")

        #获得已预约的学时（总），新预约的学时
        booked_hour, new_booked_hour, new_booked_course_list, _ = self.get_booked_course()
        self.print_log(0, "已预约学时: %d, 新预约学时: %d" %(booked_hour, new_booked_hour))
        self.dump_course_list(self.new_booked_course_json_file, new_booked_course_list)
    
        #邮件通知
        if self.have_email and (try_count>0 or self.force_send_email):
            self.print_log(2, "Sending Email...")
            msg = self.list2html(new_booked_course_list)
            msg += self.list2html(course_dict_list_sorted)
            self.email_sender.send("EPC Bookable Course", msg)

    def run_manual_strategy(self):
        '''
        运行手动策略
        1. 手动标记需要取消的课程以及预约的课程（在对应的json文件给对应课程添加'mark'键）
        2. 自动预约和取消
        '''
        course_to_cancel = []
        course_to_submit = []
        course_dict_list = self.load_course_list(self.new_booked_course_json_file)
        for course_dict in course_dict_list:
            if 'mark' in course_dict.keys():
                course_to_cancel.append(course_dict)
        
        course_dict_list = self.load_course_list(self.sorted_released_course_json_file)
        for course_dict in course_dict_list:
            if 'mark' in course_dict.keys():
                course_to_submit.append(course_dict)
        
        for course_dict in course_to_cancel:
            success = self.submit_course(course_dict, 'cancel')
            if success:
                self.print_log(2, "Cancel course: %s success" %course_dict['预约单元'])
            else:
                self.print_log(2, "Cancel course: %s failed" %course_dict['预约单元'])
        for course_dict in course_to_submit:
            success = self.submit_course(course_dict, 'submit')
            if success:
                self.print_log(2, "Submit course: %s success" %course_dict['预约单元'])
            else:
                self.print_log(2, "Submit course: %s failed" %course_dict['预约单元'])

    def login(self):
        '''登录EPC网站
        '''
        data = {
            "submit_type": "user_login",
            "name": self.ustc_id,
            "pass": self.ustc_pwd,
            "user_type": "2",
            "Submit": "LOG IN"
        }

        resp = self.session.post(url=self.URL_LOGIN, data=data)
        if resp.status_code !=200 and "登录失败" in resp.text:
            self.print_log(1, "Login failed")
            exit(1)
        else:
            self.print_log(0, "Login success")

    def get_booked_course(self, select='all'):
        '''打印课程预约记录表
        '''
        data = {
            "querytype": select  #all: 全部预约，new: 新预约
        }
        
        retry_time = 3
        while retry_time > 0:
            resp = self.session.post(url=self.URL_BOOKED, data=data)
            if resp.status_code != 200: 
                self.print_log(1, "Get booked course failed")
                retry_time -= 1
            else:
                break
        else:
            self.print_log(1, "Get booked course failed %d times, exit"%(3-retry_time))
            exit(1)
        
        # with open("booked.html", "w", encoding='gbk') as f:
        #     f.write(resp.text)
        course_dict_list = []

        html = etree.HTML(resp.text)
        course_tr_list = html.xpath('//form/tr[@bgcolor="#ffe6ff"]')
        for course_tr in course_tr_list:
            course_dict = {}
            text_list = course_tr.xpath('./td//text()')
            course_dict['zoom课堂ID与密码'] = text_list[0]
            course_dict['预约单元'] = text_list[1]
            course_dict['教师'] = text_list[2]
            course_dict['学时'] = text_list[3]
            course_dict['教学周'] = text_list[5]
            course_dict['星期'] = text_list[6]
            course_dict['上课时间date'] = text_list[7]
            course_dict['上课时间time'] = text_list[8]
            course_dict['课程状态'] = text_list[11].strip()

            #获得取消课程的url
            course_form = course_tr.getparent()
            course_dict['_url'] = course_form.get('action')

            course_dict_list.append(course_dict)
        
        new_booked_course_list = []
        for course_dict in course_dict_list:
            if course_dict['课程状态'] == '预约中':
                new_booked_course_list.append(course_dict)
        
        booked_hour = int(re.search(r'已预约的交流英语学时:(\d+)', resp.text).group(1))
        finished_hour = int(re.search(r'已获得的交流英语学时:(\d+)', resp.text).group(1))
        # missed_hour = int(re.search(r'预约未上的交流英语学时:(\d+)', resp.text).group(1))
        new_booked_hour = booked_hour - finished_hour

        return booked_hour, new_booked_hour, new_booked_course_list, course_dict_list

    def get_released_course(self, select='topic'):
        '''获得可预约课程
        '''
        retry_time = 3
        while retry_time > 0:
            resp = self.session.get(self.URL_BOOKABLE[select])
            if (resp.status_code != 200): 
                self.print_log(1, "Get released course failed")
                retry_time -= 1
            else:
                break
        else:
            self.print_log(1, "Get released course failed %d times, exit"%(3-retry_time))
            exit(1) 
        
        # with open("bookable.html", "w", encoding='gbk') as f:
        #     f.write(resp.text)
        
        html = etree.HTML(resp.text)

        course_dict_list = []
        course_form_list = html.xpath('//form[@action]')
        for course_form in course_form_list:
            course_dict = {}
            text_list = course_form.xpath('./tr/td//text()')
            course_dict['预约单元']     = text_list[0]
            course_dict['教学周']       = text_list[1]
            course_dict['星期']         = text_list[2]
            course_dict['教师']         = text_list[3]
            course_dict['学时']         = text_list[4]
            course_dict['上课时间date'] = text_list[5]
            course_dict['上课时间time'] = text_list[6]
            course_dict['教室']         = text_list[7]
            course_dict['可预约人数']    = text_list[12]
            course_dict['已预约人数']    = text_list[13]
            course_dict['课件']         = course_form.xpath('./tr/td[12]/a/@href')[0] if course_form.xpath('./tr/td[12]/a/@href') else ''
            course_dict['_url']         = course_form.xpath('./@action')[0]

            operation = course_form.xpath('./tr/td[13]//text()')[1].strip()
            #如果operation为空，要么可以预约，要么已经预约过了，需要进一步获得<input>的类型
            input_submit = course_form.xpath('./tr/td[13]/input[@type="submit"]/@value')
            if not operation:
                operation = input_submit[0]
            course_dict['operation'] = operation

            course_dict_list.append(course_dict)
        return course_dict_list
    
    def add_priority(self, course_dict_list):
        '''添加优先级
        '''
        def get_nearest_time(time_str):
            def get_middle_time(s):
                #"08:00-09:30"
                def clock_to_int(clock):
                    h, m = clock.split(':')
                    return int(h) * 60 + int(m)
                t1, t2 = s.split('-')
                return (clock_to_int(t1) + clock_to_int(t2))//2
            
            std_time = ["08:00-09:30","10:00-11:30","14:00-15:30","16:00-17:30","19:00-20:30"]
            if time_str in std_time:
                return time_str
            
            time_boundary = [570, 840, 930, 1140] #["9:30", "14:00", "15:30", "19:00"]

            t_middle = get_middle_time(time_str)
            idx = 0
            for bound in time_boundary:
                if t_middle < bound:
                    break
                idx += 1
            return std_time[idx]

        for course_dict in course_dict_list:
            if self.no_offline_course:
                if '东区' in course_dict['预约单元'] or '西区' in course_dict['预约单元']:
                    course_dict['优先级'] = '0'
                    continue
            course_time = get_nearest_time(course_dict['上课时间time']) #标准化的时间
            priority_int = self.wday_perfer[course_dict['星期']][course_time]
            course_dict['优先级'] = str(priority_int)
        return course_dict_list

    def sort_by_priority(self, course_dict_list):
        '''根据课程的优先级排序
        '''
        course_dict_list_sorted = sorted(course_dict_list, key=lambda x: int(x['优先级']), reverse=True)
        course_dict_list_sorted_by_week = sorted(course_dict_list_sorted, key=lambda x: x['教学周'])
        return course_dict_list_sorted_by_week
    
    def submit_course(self, course_dict, cmd='submit'):
        '''提交课程
        '''
        data = {
            "submit_type": "book_%s" % cmd  #book_submit/book_cancel
        }

        resp = self.session.post(url=self.URL_ROOT + course_dict["_url"], data=data)
        if (resp.status_code == 200 and "操作失败" not in resp.text):
            return True
        return False

    def try_submit_course(self, course_dict_list, new_booked_course_list):
        try_count = 0
        for course_dict in course_dict_list:
            if self.booked_score >= self.max_book_score:
                break
            if course_dict['优先级'] != '0':    #跳过优先级为0的课程
                course_week = int(course_dict['教学周'][1:-1])
                if '预 约' == course_dict['operation'] and course_week in self.filter_week:     #尝试预约可选课程
                    try_count += 1
                    success = self.submit_course(course_dict, cmd='submit')
                    if success:
                        self.booked_score += int(course_dict['学时'])
                        self.print_log(2, "Submit course success: %s" % course_dict['预约单元'])
                    else:
                        self.print_log(2, "Submit course failed: %s" % course_dict['预约单元'])
        
        if new_booked_course_list and (self.booked_score >= self.max_book_score):
            #找到可选课程里周数最小，优先级更高的课程。因为已经排序，故只需看第一个
            for course_dict in course_dict_list:
                if course_dict['优先级'] != '0':
                    min_week = int(course_dict['教学周'][1:-1])
                    min_week_course = course_dict
                    break
            if not min_week_course:
                return try_count
            
            #找到已经预约的课程里周数最大的课程
            new_booked_course_list.sort(key=lambda course: course['教学周'], reverse=True)
            max_week = int(new_booked_course_list[0]['教学周'])
            max_week_course = new_booked_course_list[0]

            if min_week < max_week: #尝试退掉已选的课程，并选择周数小的课程
                try_count += 1
                self.print_log(2, "Found better course than booked course")

                course_dict = max_week_course
                success = self.submit_course(course_dict, cmd='cancel')
                if success:
                    self.print_log(2, "Cancel course: %s success" %course_dict['预约单元'])
                else:
                    self.print_log(2, "Cancel course: %s failed" %course_dict['预约单元'])

                course_dict = min_week_course
                success = self.submit_course(course_dict, 'submit')
                if success:
                    self.print_log(2, "Submit course: %s success" %course_dict['预约单元'])
                else:
                    self.print_log(2, "Submit course: %s failed" %course_dict['预约单元'])
        
        return try_count

    def print_released_course_list(self, course_dict_list):
        if self.silent:
            return
        for course_dict in course_dict_list:
            print("%-30s %-10s %s %s %s %s %s %s %s/%s" % (
                course_dict['预约单元'], 
                course_dict['教师'], 
                course_dict['上课时间date'],
                course_dict['上课时间time'],
                course_dict['教学周'], 
                course_dict['星期'],
                course_dict['优先级'],
                course_dict['operation'],
                course_dict['已预约人数'],
                course_dict['可预约人数']
            ))
    
    def dump_course_list(self, file, course_dict_list):
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(course_dict_list, f, ensure_ascii=False, indent=4)

    def load_course_list(self, file):
        with open(file, 'r', encoding='utf-8') as f:
            course_dict_list = json.load(f)
        return course_dict_list
    
    def list2html(self, course_dict_list):
        # 若数组为空, 则返回空字符串
        if len(course_dict_list) == 0: return ""
        
        # 新建表格
        table = etree.Element('table', cellspacing="0", cellpadding="4px", border="1")

        # 新建表头
        tr = etree.SubElement(table, 'tr')
        keys = list(course_dict_list[0].keys())
        keys.remove("_url")
        for key in keys:
            th = etree.SubElement(tr, 'th')
            th.text = key

        # 循环插入EPC课程列表中的数据
        for course_dict in course_dict_list:
            tr = etree.SubElement(table, 'tr')
            for key in keys:
                td = etree.SubElement(tr, 'td', align = "center")
                try:
                    td.text = course_dict[key]
                except:
                    td.text = str(course_dict[key])
        
        return etree.tostring(table, pretty_print=True, encoding="utf-8").decode("utf-8")
    
    def print_log(self, level, msg):
        t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        if level == 0:
            if not self.silent:
                print("[INFO] %s %s" %(t, msg))
        elif level == 1:
            print("[ERROR] %s %s" %(t, msg))
        elif level == 2:
            print("[IMPORTANT] %s %s" %(t, msg))
        else:
            print("[UNKNOWN] %s %s" %(t, msg))