import time, os

time.sleep(5)
for task_id in ['bash-adc9l8gu', 'bash-x9b30g3u']:
    log = f"C:/Users/vijay/.kimi/sessions/33ec872710ffbd8528348d289b641527/803ef793-1384-43d3-9261-908cc12dd223/tasks/{task_id}/output.log"
    if os.path.exists(log):
        with open(log) as f:
            content = f.read()
        print(f"--- {task_id} ---")
        print(content[-500:] if len(content) > 500 else content)
    else:
        print(f"{task_id}: log not found")
