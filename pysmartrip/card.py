from .trip import Trip

import calendar
import datetime as dt
import csv
import json

USAGE_HISTORY_URL = "https://smartrip.wmata.com/Card/UsageReport/Index"
GET_EXCEL_URL = "https://smartrip.wmata.com/Card/UsageReport/GetExcel"


class SmarTripCard:
    def __init__(self, ctx, card_id: str):
        self.ctx = ctx
        self.card_id = card_id

    def __repr__(self):
        return f"SmarTripCard({self.card_id})"

    def __str__(self):
        return f"SmarTripCard({self.card_id})"
    
    def _get_trips_from_csv(self, params):
        const = {
            "TransactionStatus": "Successful",
            "cardId": self.card_id,
        }
        r = self.ctx.session.get(GET_EXCEL_URL, params=params | const)
        if r.ok:
            return [Trip.from_csv(line) for line in r.text.split("\n")[1:][::-1]]
        return None

    def _get_month_results(self, month: int, year: int):
        date_fmt = "%m/%d/%Y %H:%M:%S"
        last_day = calendar._monthlen(year, month)
        start = dt.datetime(year, month, 1, 0, 0)
        end = dt.datetime(year, month, last_day, 23, 59)
        params = {
            "Month": f"{year:4}{month:02}",
            "StartDate": start.strftime(date_fmt),
            "EndDate": end.strftime(date_fmt),
            "Period": "M",
        }
        return self._get_trips_from_csv(params)

    def _get_between_results(self, start, end):
        date_fmt = "%m/%d/%Y %H:%M:%S"
        params = {
            "StartDate": start.strftime(date_fmt),
            "EndDate": end.strftime(date_fmt),
            "Period": "R",
        }
        return self._get_trips_from_csv(params)


    def _get_usage(self, year=0, month=0, start=None, end=None):
        by_month = False
        if year and month:
            by_month = True

        data = {
            "IsByMonth": str(by_month).lower(),
            "CardId": int(self.card_id),
            "BackUrl": f"~/CardSummary/Index/{self.card_id}",
            # does this matter?
            "MinStartDate": "1/1/1970+12:00:00AM",
            "SubmitButton": "True",
        }
        if by_month:
            data["SelectedMonth"] = f"{year:4}{month:02}"
        else:
            date_fmt = "%m/%d/%Y"
            data["StartDate"] = start.strftime(date_fmt)
            data["EndDate"] = end.strftime(date_fmt)

        r = self.ctx._post_with_rvt(f"{USAGE_HISTORY_URL}/{self.card_id}", data)
        if r.ok:
            if by_month:
                return self._get_month_results(month, year)
            else:
                return self._get_between_results(start, end)
        return None


    def get_trips_by_month(self, month: int, year: int):
        """
        Gets all trips taken in a specific month
        : param month: int representing the month (1-12)
        : param year: int representing the year
        """
        return self._get_usage(month=month, year=year)


    def get_trips_between(self, start_date, end_date):
        """
        Gets all trips between the start and end date.
        : param start_date: string (MM/DD/YYYY) or datetime object
        : param end_date: string (MM/DD/YYYY) or datetime object
        """
        start = None
        end = None
        date_fmt = "%m/%d/%Y"

        if isinstance(start_date, str) and isinstance(end_date, str):
            try:
                start = dt.datetime.strptime(start_date, date_fmt)
                end = dt.datetime.strptime(end_date, date_fmt)
                end += dt.timedelta(hours=23, minutes=59)
            except:
                raise Exception("improperly formatted date (mm/dd/yyyy)")
        else:
            start = start_date
            end = end_date

        # the API only supports getting a maximum of 31 days, do in chunks
        results = []
        if end - start > dt.timedelta(days=31):
            cur = start
            chunk_end = cur + dt.timedelta(days=31)
            while chunk_end < end:
                results += self._get_usage(start=cur, end=chunk_end)
                cur = chunk_end
                if end - chunk_end >= dt.timedelta(days=31):
                    chunk_end += dt.timedelta(days=31)
                else:
                    chunk_end = end
        else:
            results = self._get_usage(start=start, end=end)
        return results
