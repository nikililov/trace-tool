# import selectors
import subprocess
from datetime import datetime as dt, timedelta
from pathlib import Path
from threading import Thread
from typing import Dict, List
from config_reader import get_app_log, get_results_dir
from trace_logger import logger

logging = logger


def hourly_iter(start: dt, finish: dt) -> iter:
    while finish > start:
        yield start
        start = start + timedelta(hours=1)


def std_iter(stdout: iter, stderr: iter) -> iter:
    for line in stdout:
        yield line
    for err in stderr:
        yield err


def mk_dir(directory: Path):
    try:
        directory.mkdir(parents=True)
    except OSError as e:
        logging.error(f"Directory {str(directory)} can not be created: {e}")
        raise e


class TraceTool:

    def __init__(self, params: Dict):
        self._params = params
        self.curr_datetime: dt = dt.now()

    @property
    def params(self):
        return self._params

    @params.setter
    def params(self, params: Dict):
        self._params = params

    def _process_params(self):
        # Process filter
        self.filter: Dict[str, str] = self._params["filter"]
        self.filter_type: str = self.filter["type"]
        if not self.filter_type:
            raise ValueError("No filter type is provided!")
        self.filter_value: str = self.filter["value"]
        if not self.filter_value:
            raise ValueError("No filter value is provided!")

        # Process period
        self.period: Dict[str, str] = self._params["period"]
        period_from: str = self.period["from"]
        self.datetime_from: dt = dt.strptime(period_from, '%Y-%m-%d %H:%M:%S')
        if not self.datetime_from:
            raise ValueError("No period 'from' is provided!")
        period_to: str = self.period["to"]
        self.datetime_to: dt = dt.strptime(period_to, '%Y-%m-%d %H:%M:%S')
        if not self.datetime_to:
            raise ValueError("No period 'to' is provided!")
        self.hours: List[dt] = self.get_hours()

        # Process apps
        self.apps: Dict[str, List[str]] = self._params["apps"]
        if self.apps:
            for app, hosts in self.apps.items():
                if not hosts:
                    raise ValueError(f"No hosts are provided for app: {app}.")
        else:
            raise ValueError("No apps are provided!")

    # make list of hours
    def get_hours(self):
        if self.datetime_from > self.datetime_to:
            logging.error(f"Period 'from' {self.datetime_from} is bigger than period 'to' {self.datetime_to}")
            raise ValueError(f"Period 'from' {self.datetime_from} is bigger than period 'to' {self.datetime_to}")
        return [hour for hour in hourly_iter(self.datetime_from, self.datetime_to)]

    def process_request(self):
        # mk trace dir
        # Ex. /aux1/octrace-tool/results
        results_dir: Path = get_results_dir()
        # 2022020513181517
        trace_datetime: str = self.curr_datetime.strftime('%Y%m%d%H%M%S')
        # Ex. /aux1/trace-tool/results/20220209115607_0x92ffbea532400ad
        trace_dir: Path = Path(results_dir, f"{trace_datetime}_{self.filter_value}")
        mk_dir(trace_dir)

        threads: List = []

        for app, hosts in self.apps.items():
            # mk app result dir
            # Ex. # Ex. /aux1/trace-tool/results/20220209115607_0x92ffbea532400ad/USSDGW
            app_result_dir: Path = Path(trace_dir, app)
            mk_dir(app_result_dir)

            # get from config app log for tracing
            # Ex. /aux1/browser/logs/browser_(datetime).log
            app_log: Path = get_app_log(app.upper())
            for hour in self.hours:
                # app log for tracing
                # Ex. 2022020519
                date_hour: str = hour.strftime("%Y%m%d%H")
                # Ex. /aux1/browser/logs/browser_2021041110.log
                curr_log: Path = Path(str(app_log).replace("(datetime)", date_hour))

                # mk hour result dir
                # Ex. /aux1/trace-tool/results/20220209115607_0x92ffbea532400ad/USSDGW/2022020519
                hour_result_dir: Path = Path(app_result_dir, date_hour)
                mk_dir(hour_result_dir)

                for host in hosts:
                    # mk host result dir
                    # Ex. /aux1/trace-tool/results/20220209115607_0x92ffbea532400ad/USSDGW/2022020519/ussdgw1
                    host_result_dir: Path = Path(hour_result_dir, host)
                    mk_dir(host_result_dir)
                    print(host_result_dir)

                    t = Thread(target=self.do_trace, args=(app, host, host_result_dir, str(curr_log)))
                    threads.append(t)
                    t.start()
                    # self.do_trace(app, host, str(curr_log))
        for t in threads:
            t.join()

    def do_trace(self, app: str, host: str, host_result_dir: Path, log: str):
        cmd = f"nice -n 19 ionice -c2 -n7 /usr/bin/zgrep -aE {self.filter_value} {log}"
        print(f"Processing {app} at {host}: {log}")
        logging.info(f"Processing {app} at {host}: {log}")
        result_file: Path = Path(host_result_dir, "result.txt")
        try:
            with open(str(result_file), 'w') as file:
                with subprocess.Popen(['ssh', '-oBatchMode=yes', f"trace-tool@{host}", cmd], stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:

                    # stderr_resp = proc.stderr.read().decode('utf-8', 'ignore')
                    # if len(stderr_resp) != 0:
                    #     print(f"Stderr: {stderr_resp}")
                    # else:
                    for line in std_iter(iter(proc.stdout.readline, b''), iter(proc.stderr.readline, b'')):
                        file.write(line.decode("utf-8"))
        except FileNotFoundError as e:
            logging.error(f"File not found: {e}")
            raise e
        except OSError as e:
            logging.error(f"OS Error: {e}")
            raise e
        except Exception as e:
            logging.error(f"Can not process: {e}")
            raise e

        # selector = selectors.DefaultSelector()
        # selector.register(proc.stdout, selectors.EVENT_READ)
        # selector.register(proc.stderr, selectors.EVENT_READ)
        # eof = False
        # while not eof:
        #     for key, event in selector.select():
        #         if key.fileobj is proc.stdout:
        #             for line in iter(proc.stdout.readline, b''):
        #                 print(line)
        #             eof = True
        #         else:
        #             for err in iter(proc.stderr.readline, b''):
        #                 print(err)
        #             eof = True
        # selector.close()

    # TOO SLOW
    # def do_trace(self, host: str, log: str):
    #     ssh_client = paramiko.SSHClient()
    #     ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    #     ssh_client.connect(hostname=host, username="trace-tool", password="tracetool")
    #     with ssh_client.open_sftp() as sftp_client:
    #        # sftp_client.
    #         with sftp_client.open(log, 'r') as remote_log:
    #             for line in remote_log:
    #                 if self.filter_value in line:
    #                     print(line)
    #     # stdin, stdout, stderr = ssh_client.exec_command("hostname")
    #     # print(f"Output: {stdout.readline()}, Err: {stderr.readline()}")
    #     #with ssh_client.

    def run(self):
        self._process_params()
        self.process_request()
