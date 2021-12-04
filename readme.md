### 说明

本项目基于[Arsennnic/ustc-epc-bot: 中国科学技术大学EPC课程自动预约/优化脚本 (github.com)](https://github.com/Arsennnic/ustc-epc-bot)修改而来。

本项目针对的是openwrt、树莓派等嵌入式平台（当然也可以运行在PC上），主要交互逻辑是命令行。

本项目脚本只会运行一次，需要结合linux `crontab`等工具定时运行脚本

主要不同：

1. 删除UI界面，纯命令行：使之能运行在openwrt等平台
2. 代码仅针对Topical Discussion选课
3. 修改选课逻辑：
   - 自动模式，配置文件可以设置不同时间段的优先级
   - 手动替换课程模式，以达到更准确的控制

### 依赖

python 依赖的库如下：

```
requests
lxml
```

### 使用说明

0. 安装依赖

   ```bash
   pip install -r requirements.txt
   ```

1. 将`config-tamplate.json`复制为`config.json`，并填写相关字段

2. 字段说明

   1. `ustc_id`, `ustc_pwd`：epc网站用户名和密码
   2. `email_rcv_addr`：接收邮箱地址。保证在该邮箱收到邮件时，手机等设备能第一时间推送。可以和发送邮箱地址相同。
   3. `email_send_addr`：发送邮箱地址。用来发送邮件的邮件地址，需要开启IMAP/SMTP服务，并获得授权码（参考QQ邮箱说明[什么是授权码，它又是如何设置？_QQ邮箱帮助中心](https://service.mail.qq.com/cgi-bin/help?subtype=1&&id=28&&no=1001256)）。可以使用一些不重要的邮箱。
   4. `email_smtp_addr`：发送邮箱smtp服务器地址
   5. `email_auth_code`：授权码
   6. `wday_perfer`：每一时间段的选择优先级，5为最高，**0表示不能选该时间段**。自动选课模式下，会优先选择周数小的，相同时再根据此处的优先级进行选择。
   7. `no_offline_course`：不选择线下课程（东西区课程），设置true或者false

3. 如果不使用邮箱

   在main.py中设置have_email为False，即

   ```python
   bot = Bot(config, have_email=False)
   ```

4. 其它字段：

   1. `filter_week`

       在`main.py`中设置`filter_week`，则脚本只选择指定周的课程。
   
       ```python
       filter_week = [13, 14, 15, 16]
       bot = Bot(config, filter_week=filter_week)
       ```
   
       如果不传`filter_week`可变参数，则默认可选任意周的课程
   
   2. `force_send_email`
   
       设置为true时，则每次运行都会发送邮件
   
4. **运行**

   方式一：

   ```bash
   python main.py
   ```

   该方式会获得发布的课程，并自动尝试选择优先级高的课程

   当有更好的课程时，会发送邮件通知

   缺点：当课程冲突，预约时间已满时，无法自动退课，然后选择更好的课程（比如周数更短）

   方式二：
   
   ```bash
   python main_manual.py
   ```

   1. 首先按照方式一运行main.py，会生成`course_to_cancel.json`和`course_to_submit.json`。

   2. 然后在需要取消/选择的课上添加`"mark"`作为key。
   
       如在`course_to_cancel.json`中进行标记：
       
       ```json
           {
               "zoom课堂ID与密码": "xxxx",
               "预约单元": "xxx",
               "教师": "xxx",
               "学时": "xxx",
               "教学周": "xxx",
               "星期": "xxx",
               "上课时间date": "xxx",
               "上课时间time": "xxx",
               "课程状态": "预约中",
               "_url": "xxxx"
           },
       ```
   
       修改为：
       
       ```json
           {
            	"mark": "",
               "zoom课堂ID与密码": "xxxx",
               "预约单元": "xxx",
               "教师": "xxx",
               "学时": "xxx",
               "教学周": "xxx",
               "星期": "xxx",
               "上课时间date": "xxx",
               "上课时间time": "xxx",
               "课程状态": "预约中",
               "_url": "xxxx"
           },
       ```
       
       其中"mark"对应的值随意。类似的，在`course_to_submit.json`中标记。之后运行`main_manual.py`便会按照顺序依次退掉标记的课程，以及选择标记的课程。
       

### TODO

1. ~~添加检测课程变动逻辑，使其仅当有课程变动时才发送邮件通知（为了令其作为一个服务运行在openwrt上）~~
2. ~~添加异常处理逻辑，例如目前如果获得发布课程的请求超时失败，目前会直接退出，如何添加一些错误重试逻辑~~
3. 增加多线程操作（其实不是很重要，能自动在发布课程时选到课程即可，不需要那么快）

