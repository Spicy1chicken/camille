from utlis.third_party_sdk import ThirdPartySdk
from utlis.simulate_click import SimulateClick
from utlis import print_msg, write_xlsx
from multiprocessing import Process
import multiprocessing
import argparse
import random
import signal
import frida
import time
import sys
import os

try:
    import click
except:
    class click:
        @staticmethod
        def secho(message=None, **kwargs):
            print(message)

        @staticmethod
        def style(**kwargs):
            raise Exception("unsupported style")
try:
    from shutil import get_terminal_size as get_terminal_size
except:
    try:
        from backports.shutil_get_terminal_size import get_terminal_size as get_terminal_size
    except:
        pass

banner = """
-----------------------------------------------------------


 .o88b.  .d8b.  .88b  d88. d888888b db      db      d88888b 
d8P  Y8 d8' `8b 88'YbdP`88   `88'   88      88      88'     
8P      88ooo88 88  88  88    88    88      88      88ooooo 
8b      88~~~88 88  88  88    88    88      88      88~~~~~ 
Y8b  d8 88   88 88  88  88   .88.   88booo. 88booo. 88.     
 `Y88P' YP   YP YP  YP  YP Y888888P Y88888P Y88888P Y88888P 
                                                                                     
            https://github.com/zhengjim/camille
-------------------------------------------------------------\n
"""


def show_banner():
    colors = ['bright_red', 'bright_green', 'bright_blue', 'cyan', 'magenta']
    try:
        click.style('color test', fg='bright_red')
    except:
        colors = ['red', 'green', 'blue', 'cyan', 'magenta']
    try:
        columns = get_terminal_size().columns
        if columns >= len(banner.splitlines()[1]):
            for line in banner.splitlines():
                click.secho(line, fg=random.choice(colors))
    except:
        pass


def frida_hook(app_name, use_module, wait_time=0, is_show=True, execl_file=None, isattach=False):
    """
    :param app_name: 包名
    :param use_module 使用哪些模块
    :param wait_time: 延迟hook，避免加壳
    :param is_show: 是否实时显示告警
    :param execl_file 导出文件
    :param isattach 使用attach hook

    :return:
    """

    def my_message_handler(message, payload):
        """ 消息处理 """
        if message["type"] == "error":
            print(message)
            os.kill(os.getpid(), signal.SIGTERM)
            return
        if message['type'] == 'send':
            data = message["payload"]
            if data["type"] == "notice":
                alert_time = data['time']
                action = data['action']
                arg = data['arg']
                messages = data['messages']
                stacks = data['stacks']
                subject_type = tps.is_third_party(stacks)

                if is_show:
                    print("------------------------------start---------------------------------")
                    print("[*] {0}，APP行为：{1}、行为主体：{2}、行为描述：{3}、传入参数：{4}".format(
                        alert_time, action, subject_type, messages, arg.replace('\r\n', '，')))
                    print("[*] 调用堆栈：")
                    print(stacks)
                    print("-------------------------------end----------------------------------")
                if execl_file:
                    global privacy_policy_status
                    global execl_data
                    execl_data.append({
                        'alert_time': alert_time,
                        'action': action,
                        'messages': messages,
                        'arg': arg,
                        'stacks': stacks,
                        'subject_type': subject_type,
                        'privacy_policy_status': "同意隐私政策" + privacy_policy_status.value,
                    })
            if data['type'] == "app_name":
                get_app_name = data['data']
                my_data = False if get_app_name == app_name else True
                script.post({"my_data": my_data})
            if data['type'] == "isHook":
                global isHook
                isHook = True
                script.post({"use_module": use_module})
            if data['type'] == "noFoundModule":
                print_msg('Not Found Module: ' + data['data'] + " . Please exit the check")
                session.detach()

    try:
        try:
            tps = ThirdPartySdk()
            device = frida.get_usb_device()
        except:
            device = frida.get_remote_device()
        pid = app_name if isattach else device.spawn([app_name])
    except Exception as e:
        print_msg("hook error")
        print_msg(e)
        exit()

    time.sleep(1)
    session = device.attach(pid)
    time.sleep(1)

    with open("./script.js", encoding="utf-8") as f:
        script_read = f.read()

    if wait_time:
        script_read += "setTimeout(main, {0}000);\n".format(str(wait_time))
    else:
        script_read += "setImmediate(main);\n"

    script = session.create_script(script_read)
    script.on("message", my_message_handler)
    script.load()
    time.sleep(1)
    try:
        if not isattach:
            device.resume(pid)
    except Exception as e:
        print_msg("hook error")
        print_msg(e)
        exit()

    wait_time += 1
    time.sleep(wait_time)
    if isHook:
        def stop(signum, frame):
            print_msg('You have stoped hook.')
            session.detach()
            if execl_file:
                global execl_data
                write_xlsx(execl_data, execl_file)
            exit()

        signal.signal(signal.SIGINT, stop)
        signal.signal(signal.SIGTERM, stop)
        sys.stdin.read()
    else:
        print_msg("hook fail, try delaying hook, adjusting delay time")


def agree_privacy(privacy_policy_status):
    # 等待应用启动
    time.sleep(5)
    sc = SimulateClick('screen.png')
    sc.run()
    result = sc.get_result()
    while result == 1:
        sc = SimulateClick('screen.png')
        sc.run()
        result = sc.get_result()
    if result == 2:
        privacy_policy_status.value = '后'


if __name__ == '__main__':
    show_banner()

    parser = argparse.ArgumentParser(description="App privacy compliance testing.")
    parser.add_argument("package", help="APP_NAME or process ID ex: com.test.demo01 、12345")
    parser.add_argument("--time", "-t", default=0, type=int, help="Delayed hook, the number is in seconds ex: 5")
    parser.add_argument("--noshow", "-ns", required=False, action="store_const", default=True, const=False,
                        help="Showing the alert message")
    parser.add_argument("--file", "-f", metavar="<path>", required=False, help="Name of Excel file to write")
    parser.add_argument("--isattach", "-ia", required=False, action="store_const", default=False, const=True,
                        help="use attach hook")
    parser.add_argument("--noprivacypolicy", "-npp", required=False, action="store_const", default=False, const=True,
                        help="close the privacy policy. after closing, default status is agree privacy policy")

    group = parser.add_mutually_exclusive_group()

    group.add_argument("--use", "-u", required=False,
                       help="Detect the specified module,Multiple modules are separated by ',' ex:phone,permission")
    group.add_argument("--nouse", "-nu", required=False,
                       help="Skip specified module，Multiple modules are separated by ',' ex:phone,permission")

    args = parser.parse_args()
    # 全局变量
    isHook = False

    execl_data = []

    use_module = {"type": "all", "data": []}
    if args.use:
        use_module = {"type": "use", "data": args.use}
    if args.nouse:
        use_module = {"type": "nouse", "data": args.nouse}

    if args.noprivacypolicy:
        privacy_policy_status = multiprocessing.Value('u', '后')
    else:
        privacy_policy_status = multiprocessing.Value('u', '前')
        p = Process(target=agree_privacy, args=(privacy_policy_status,))
        p.start()

    process = int(args.package) if args.package.isdigit() else args.package
    frida_hook(process, use_module, args.time, args.noshow, args.file, args.isattach)
