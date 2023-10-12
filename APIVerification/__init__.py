import datetime
from flask import request
from daba.Mongo import collection

STATUS = [
    {
        0: "Inactive",
        1: "Active",
        2: "Deleted",
        3: "Blocked"
    }
]


class APIVerification:
    def __init__(self):
        self.db_referers = collection('referers')
        self.db_monthly_access = collection('monthly_access')
        self.db_logs = collection('logs')

    def verify_request(self):
        api_key = request.headers.get('X-API-Key')
        referer = request.headers.get('Referer')

        # Verifying the API key and Referer
        referer_data = self.db_referers.getAfterCount({"Status": 1, "Key": api_key, "Referer": referer}, "CallCount")

        if not referer_data:
            return False

        # Checking the Monthly Access
        current_month = datetime.datetime.now().month
        monthly_access_data = self.db_monthly_access.getAfterCount(
            {"RefererId": referer_data["_id"], "Month": current_month}, "CallCount")
        if monthly_access_data is None:
            # Insert a new document for the current month with CallCount 1
            self.db_monthly_access.put({"RefererId": referer_data["_id"], "Month": current_month, "CallCount": 1})
        elif monthly_access_data["CallCount"] >= referer_data["Limit"]:
            return False

        # Logging the Request
        # log_data = {
        #     "IP": request.remote_addr,
        #     "URL": request.url,
        #     "Device": request.user_agent.platform,
        #     "Referer_id": referer_data["_id"],
        #     "Timestamp": datetime.datetime.now(),
        #     "Application": referer
        # }
        # self.db_logs.put(log_data)

        return True
