# -*- coding: utf-8 -*-
"""长任务管理：把 app/core 的同步函数包成后台线程，进度推给前端。

设计：
- 每个任务一个 job_id，前端用它过滤事件。
- 三种事件：job.progress / job.log / job.done / job.error。
- 任务可取消（软取消：检查 stop 标志）。
- 失败不抛到线程外，统一转成 job.error。
"""
import threading
import time
import traceback


class Job(object):
    """一个后台任务。"""

    def __init__(self, job_id, kind, emitter):
        self.job_id = job_id
        self.kind = kind
        self._emit = emitter
        self.stop_flag = threading.Event()
        self.result = None

    # ---------------------------------------------------------------- 事件

    def progress(self, label, done=0, total=0, phase=None, extra=None):
        pct = int(done * 100 / total) if total else 0
        payload = {
            "job_id": self.job_id,
            "phase": phase or self.kind,
            "label": str(label or ""),
            "done": int(done or 0),
            "total": int(total or 0),
            "percent": max(0, min(100, pct)),
        }
        if extra:
            payload.update(extra)
        self._emit("job.progress", payload)

    def log(self, line):
        self._emit("job.log", {"job_id": self.job_id, "line": str(line or "")})

    def done(self, result=None):
        self.result = result
        self._emit("job.done", {"job_id": self.job_id, "result": result or {}})

    def fail(self, message):
        self._emit("job.error", {"job_id": self.job_id, "message": str(message)})

    def stopped(self):
        return self.stop_flag.is_set()


class JobRunner(object):
    """管理所有后台任务。"""

    def __init__(self, emitter):
        self._emit = emitter
        self._jobs = {}
        self._lock = threading.Lock()
        self._seq = 0

    def new_id(self, kind):
        with self._lock:
            self._seq += 1
            return "%s-%d-%d" % (kind, int(time.time() * 1000), self._seq)

    def start(self, kind, target):
        """target(job) 在线程里执行。返回 job_id。"""
        job_id = self.new_id(kind)
        job = Job(job_id, kind, self._emit)
        self._jobs[job_id] = job

        def wrapper():
            try:
                target(job)
            except Exception as exc:
                traceback.print_exc()
                job.fail("%s: %s" % (type(exc).__name__, exc))
            finally:
                # 留一段时间给前端取结果，之后清掉
                threading.Timer(60.0, lambda: self._jobs.pop(job_id, None)).start()

        threading.Thread(target=wrapper, daemon=True,
                         name="job-" + job_id).start()
        return job_id

    def cancel(self, job_id):
        job = self._jobs.get(job_id)
        if not job:
            return False
        job.stop_flag.set()
        return True

    def get(self, job_id):
        return self._jobs.get(job_id)
