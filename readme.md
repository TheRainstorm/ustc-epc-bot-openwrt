### 说明

本项目基于[Arsennnic/ustc-epc-bot: 中国科学技术大学EPC课程自动预约/优化脚本 (github.com)](https://github.com/Arsennnic/ustc-epc-bot)修改而来。

主要不同：

1. 删除UI界面，纯命令行：使之能运行在openwrt等平台
2. 代码仅针对Topical Discussion选课
3. 修改选课逻辑：
   - 自动模式，配置文件可以设置不同时间段的优先级
   - 手动替换课程模式，以达到更准确的控制

### 使用说明

1. 将`config-tamplate.json`复制为`config.json`，并填写相关字段

2. 字段说明

   1. `ustc_id`, `ustc_pwd`：epc网站用户名和密码
   2. `email_addr`：邮箱地址
   3. `email_smtp_addr`：邮箱smtp地址，如qq邮箱为smtp.qq.com
   4. `email_auth_code`：授权码，参考QQ邮箱说明[什么是授权码，它又是如何设置？_QQ邮箱帮助中心](https://service.mail.qq.com/cgi-bin/help?subtype=1&&id=28&&no=1001256)
   5. `wday_perfer`：每一时间段的选择优先级，5为最高，**0表示不能选该时间段**

3. 如果不使用邮箱

   在main.py中设置send_email为False

   ```python
   bot = Bot(config, send_email=False)
   ```

4. 运行

   方式一：

   ```bash
   python main.py
   ```

   该方式会获得发布的课程，并尝试选择优先级高的课程

   缺点：当课程冲突，预约时间已满时，无法自动退课，然后选择更好的课程（比如周数更短）

   方式二：

   ```bash
   python main_manual.py
   ```

   1. 运行main.py后，会生成`course_to_cancel.json`和`course_to_submit.json`。

   2. 在需要取消/选择的课上添加`"mark"`作为key。

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
       
       其中"mark"对应的值随意。
       
       之后运行`main_manual.py`便会退掉该节课

### TODO

1. 添加检测课程变动逻辑，使其仅当有课程变动时才发送邮件通知（为了令其作为一个服务运行在openwrt上）
2. 添加异常处理逻辑，例如目前如果获得发布课程的请求超时失败，目前会直接退出，如何添加一些错误重试逻辑
3. 增加多线程操作（其实不是很重要，能自动在发布课程时选到课程即可，不需要那么快）
