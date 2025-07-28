# -*- coding: utf-8 -*-
"""
Created on Tue Jun  3 14:00:34 2025

@author: BAC5MC
"""

import requests
import json
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# from getpass import getpass

cookie_file = r"C:\Users\ala2bp\AppData\Local\Temp\python_cookie"
session_cookie_name = "JSESSIONID"
base_url = "https://edate.webapp.inside.bosch.cloud/edate/api"
# base_url = "http://10.4.14.199:8080/edate/api"
auth_url = "/auth/token"
details_url= "auth/sessionDetails"
projects_url = "/genericsearch/v1/Project_UserSearch/search"
tests_url = "/genericsearch/v1/TestInstance_UserSearch/search"
laboratorys_url = "/genericsearch/v1/Laboratory_UserSearch/search"
tc_url = "/genericsearch/v1/TestContainer_UserSearch/search"
allocation_url="/genericsearch/v1/Allocation_UserSearch/search"

headers_list = {
 "Accept": "*/*",
 "User-Agent": "Python request",
 "Content-Type": "application/json" 
}

def easter_date(year):
    """Computes Easter Sunday date using Anonymous Gregorian algorithm."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return datetime(year, month, day)

def count_weekends_and_holidays(start_date, end_date):
    holidays = [
        "01-01", "03-15", "05-01", "08-20",
        "10-23", "11-01", "12-25", "12-26"
    ]                                                                               # bedolgozós szomatok hiányoznak
    
    weekend_count = 0
    holiday_count = 0
    holiday_dates = []
    weekend_dates = set()

    current_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    start_date = datetime.strptime(start_date, "%Y-%m-%d")

    while current_date <= end_date:
        if current_date.weekday() >= 5:  # Szombat vagy vasárnap
            weekend_count += 1
            weekend_dates.add(current_date.date())
        if current_date.strftime("%m-%d") in holidays:
            holiday_count += 1
            holiday_dates.append(current_date.date())
        current_date += timedelta(days=1)


    for year in range(start_date.year, end_date.year + 1):
        easter = easter_date(year)
        easter_monday = easter + timedelta(days=1)
        pentecost = easter + timedelta(days=49)
        pentecost_monday = pentecost + timedelta(days=1)

        for holiday in [easter, easter_monday, pentecost, pentecost_monday]:
            if start_date <= holiday <= end_date:
                holiday_count += 1
                holiday_dates.append(holiday.date())

    # Átfedések kiszámítása
    holiday_set = set(holiday_dates)
    overlap = holiday_set & weekend_dates

    all_day = weekend_count + holiday_count - len(overlap)

    return weekend_count, holiday_count, holiday_set, all_day

def merge_intervals(intervals):
    """Merge overlapping or consecutive intervals, preserving and combining status information."""
    if not intervals:
        return [], []

    # Sort intervals by start date
    sorted_intervals = sorted(intervals, key=lambda x: x[1])
    
    # Initialize merged intervals
    merged_all_statuses = [sorted_intervals[0]]
    merged_by_status = {sorted_intervals[0][0]: [sorted_intervals[0]]}

    for current in sorted_intervals[1:]:
        current_status, current_start, current_end = current
        last_status, last_start, last_end = merged_all_statuses[-1]

        # Merge all statuses together
        if current_start <= last_end + timedelta(days=1):
            merged_all_statuses[-1] = (last_status + " / " + current_status, last_start, max(last_end, current_end))
        else:
            merged_all_statuses.append(current)

        # Merge intervals separately for each unique status
        if current_status in merged_by_status:
            last_status, last_start, last_end = merged_by_status[current_status][-1]
            if current_start <= last_end + timedelta(days=1):
                merged_by_status[current_status][-1] = (current_status, last_start, max(last_end, current_end))
            else:
                merged_by_status[current_status].append(current)
        else:
            merged_by_status[current_status] = [current]

    return merged_all_statuses, merged_by_status

def get_allocation(session: requests.Session, weekends, holidays, all_days, start, end) -> str:
    seq_payload = json.dumps({
        "filterCriteria": f"Laboratory#laboratoryId = 'L048' AND Allocation#start > '{start}' AND Allocation#end < '{end}' AND Allocation#allocationType !=''",
        "maxResults":1024,
        "resultFields":
        [
            {"fieldId": "Allocation#end","fieldAlias":"end"},
            {"fieldId": "Allocation#start","fieldAlias":"start"},
            {"fieldId": "TestInstance#actualStart", "fieldAlias": "actualStart"},
            {"fieldId": "TestInstance#actualEnd", "fieldAlias": "actualEnd"},
            {"fieldId": "Allocation#allocationType","fieldAlias":"type"},
            {"fieldId": "Allocation#resourceName","fieldAlias":"allocationResourceName"},
            {"fieldId": "Resource#resourceName","fieldAlias":"resourceName"},
            {"fieldId": "Laboratory#laboratoryName","fieldAlias":"laboratoryName"},
            {"fieldId": "Allocation#testInstanceId","fieldAlias":"testInstanceId"},
        ]
    })
    print(seq_payload)
    response = session.post(base_url+allocation_url, data=seq_payload,  headers=headers_list, cookies=session.cookies)
    all_day = calculate_days(start, end)
    working_days = all_day - all_days
    
    this_month = datetime.strptime(start, "%Y-%m-%d").strftime("%Y-%m")
    
    data = json.loads(response.text)
    print(data)
    # Csoportosítás resourceName szerint
    resource_intervals = {}
    for entry in data:
        print("ENRTY: ",entry)
        
        if entry["actualStart"] == "" or entry["actualEnd"] == "":
            print("Start: ",entry["start"])
            start_dt = datetime.fromisoformat(entry["start"])
            end_dt = datetime.fromisoformat(entry["end"])
        else:
            print("actualStart: ",entry["actualStart"])
            start_dt = datetime.fromisoformat(entry["actualStart"])
            end_dt = datetime.fromisoformat(entry["actualEnd"])
        resource = entry["resourceName"]
        # start_dt = datetime.fromisoformat(entry["actualStart"])
        # end_dt = datetime.fromisoformat(entry["actualEnd"])
        allocation_type = entry["type"]
        resource_intervals.setdefault(resource, []).append((allocation_type, start_dt, end_dt))
    print(resource_intervals) 

    resource_usage = {}
    
    resource_usage_ = {}
    
    print(resource_intervals.items())

    for resource, intervals in resource_intervals.items():
        resource_group_usage_by_status = {}
        print("INTERVALS: ", intervals)
        merged_intervals , merged_by_status= merge_intervals(intervals)
        total_used_days = 0
        total_used_days_ = 0
        print("MERGED_BY_STATUS: ", merged_by_status)
        for status_type in merged_by_status:
            total_used_days_ = 0
            print("STATUS: ", status_type)
            for allocation_type_, start_dt_, end_dt_ in merged_by_status[status_type]:
                if status_type != allocation_type_:
                    print("error :", status_type," nnn", allocation_type_)
                usage_days_ = calculate_days(start_dt_.strftime("%Y-%m-%d"), end_dt_.strftime("%Y-%m-%d"))
                _, _, _, free_days_ = count_weekends_and_holidays(start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
                total_used_days_ += usage_days_ - free_days_
            #0
            usage_percentage_ = (total_used_days_ / working_days) * 100
            print("type:", status_type)
            print("total_used_days: ",total_used_days_)
            resource_group_usage_by_status[status_type] = {
                "used days": total_used_days_,
                "percentage": usage_percentage_,
                "worked days": working_days,
                "weekends": weekends,
                "holidays": holidays,
                "actual_month" : this_month,
                "type" : status_type
            }
        resource_usage_[resource] = [resource_group_usage_by_status]
        
        for allocation_type, start_dt, end_dt in merged_intervals:
            usage_days = calculate_days(start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
            _, _, _, free_days = count_weekends_and_holidays(start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
            total_used_days += usage_days - free_days
        #0
        usage_percentage = (total_used_days / working_days) * 100

        resource_usage[resource] = {
            "used days": total_used_days,
            "percentage": usage_percentage,
            "worked days": working_days,
            "weekends": weekends,
            "holidays": holidays,
            "actual_month" : this_month,
            "type" : allocation_type
        }

    small_percentage = resource_usage.get("SMALL noise chamber", {}).get("percentage", 0)
    big_percentage = resource_usage.get("BIG noise chamber", {}).get("percentage", 0)

    print(json.dumps(resource_usage_, indent=2))

    return response.text, small_percentage, big_percentage, resource_usage, resource_usage_
    # return response.text

# Függvény az időtartam kiszámítására
def calculate_days(start_date, end_date):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    weekends, holidays, holiday_dates, all_days = count_weekends_and_holidays(start_date, end_date)
    
    return (end - start).days + 1

def get_last_day_of_current_month():
    today = datetime.today()
    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)
    last_day = next_month - timedelta(days=1)
    return last_day.strftime("%Y-%m-%d")

def plot_resource_usage(all_resource_usages, combined=False):
    months = [int(entry["actual_month"][5:]) for entry in all_resource_usages["BIG noise chamber"]]

    if combined:
        combined_percentages = [
            (big["percentage"] + small["percentage"])/2 #200% osztva 2-vel
            for big, small in zip(all_resource_usages["BIG noise chamber"], all_resource_usages["SMALL noise chamber"])
        ]
        plt.bar(months, combined_percentages, label="Combined BIG and SMALL noise chamber")
    else:
        big_percentages = [entry["percentage"] for entry in all_resource_usages["BIG noise chamber"]]
        small_percentages = [entry["percentage"] for entry in all_resource_usages["SMALL noise chamber"]]
        
        plt.bar(months, big_percentages, width=0.4, align='center', label="BIG noise chamber")
        plt.bar(months, small_percentages, width=0.4, align='edge', label="SMALL noise chamber")
    # Add 60% red line
    plt.axhline(y=60, color='red', linestyle='--', linewidth=2, label='60% Limit')
    plt.xlabel("Date")
    plt.ylabel("Percentage", )
    plt.title("Resource Usage by Month")
    plt.legend()
    plt.show()

def plot_resource_usage_(all_resource_usages, combined=False):
    # months = [int(entry["actual_month"][5:]) for entry in all_resource_usages["BIG noise chamber"]]
    # actual_months = [entry['actual_month'] for entry in all_resource_usages["BIG noise chamber"]]
    
    big_monthly = extract_monthly_percentages(all_resource_usages['BIG noise chamber'])
    small_monthly = extract_monthly_percentages(all_resource_usages['SMALL noise chamber'])
    
    # Combine months and sort
    all_months = sorted(set(big_monthly.keys()).union(small_monthly.keys()))
    
    # Prepare data for plotting
    big_values = [big_monthly.get(month, 0) for month in all_months]
    small_values = [small_monthly.get(month, 0) for month in all_months]
    combined_values = [(b + s)/2 for b, s in zip(big_values, small_values)]
    
    # Plotting
    x = range(len(all_months))
    width = 0.25
    
    plt.figure(figsize=(12, 6))
    plt.bar([i - width for i in x], big_values, width=width, label='BIG Chamber')
    plt.bar(x, small_values, width=width, label='SMALL Chamber')
    plt.bar([i + width for i in x], combined_values, width=width, label='Combined')
    
    # Add 60% red line
    plt.axhline(y=60, color='red', linestyle='--', linewidth=2, label='60% Limit')

    plt.xticks(ticks=x, labels=all_months)
    plt.ylabel('Percentage Usage')
    plt.title('Monthly Percentage Usage in BIG and SMALL Chambers')
    plt.legend()
    plt.tight_layout()
    plt.savefig("chamber_usage_bar_chart.png")
    plt.show()

# Helper function to sum percentages per month
def extract_monthly_percentages(chamber_data):
    monthly = {}
    for entry in chamber_data:
        if isinstance(entry, list):
            for category_dict in entry:
                for category in category_dict.values():
                    month = category['actual_month']
                    monthly[month] = monthly.get(month, 0) + category['percentage']
        elif isinstance(entry, dict):
            month = entry['actual_month']
            monthly[month] = monthly.get(month, 0) + entry['percentage']
    return monthly

def login(session: requests.Session) -> None:
    print("First usage, please login")
    # user_id = input("User ID: ")
    # pwd = getpass()
    user_id="BAC5MC"
    pwd = "NAistheway20252"

    session.auth = (user_id.strip(), pwd.strip())

    response = session.get(base_url+auth_url, headers=headers_list)
    # response = session.get(base_url+details_url, headers=headers_list)
    print("Cookies after auth:")
    print(session.cookies.get_dict())

if __name__ == "__main__":
    

    # data = main()
    
    session = requests.Session()

    while True:
        if not session_cookie_name in session.cookies.keys():
            login(session)
        else:
            all_data = {}
            try:
                while True:
                    try:
                        user_input = input("Add meg a dátumot ebben a formátumban: ÉÉÉÉ-HH-NN (pl. 2025-06-11): ")
                        if user_input == "exit":
                            break
                        start_date_ = datetime.strptime(user_input, "%Y-%m-%d")
                        break  # helyes formátum, kilépünk a ciklusból
                    except KeyboardInterrupt:
                        exit()
                        break
                    except ValueError:
                        print("Hibás formátum! Kérlek, próbáld újra.")

                print("A dátum helyes:", start_date_.strftime("%Y-%m-%d"), "Indul a lekérdezés")

                start_date_=start_date_.strftime("%Y-%m-%d")
                # start_date_ = "2024-01-01"
                # end_date_ = "2025-01-30" get_last_day_of_current_month()
                end_date_ = get_last_day_of_current_month()
                
                start_date = datetime.strptime(start_date_, "%Y-%m-%d")
                end_date = datetime.strptime(end_date_, "%Y-%m-%d")
                
                current = start_date
               
                all_resource_usages = {
                    "BIG noise chamber": [],
                    "SMALL noise chamber": []
                }
                all_resource_usages_ = {
                    "BIG noise chamber": [],
                    "SMALL noise chamber": []
                }
                while current <= end_date:
                    
                    # Hónap első napja
                    first_day = current.replace(day=1)
    
                    # Következő hónap első napja
                    if current.month == 12:
                        next_month = current.replace(year=current.year + 1, month=1, day=1)
                    else:
                        next_month = current.replace(month=current.month + 1, day=1)
    
                    # Hónap utolsó napja: a következő hónap első napja mínusz egy nap
                    last_day = next_month - timedelta(days=1)
                    # print(f"Hónap: {first_day.strftime('%Y-%m')}, Kezdete: {first_day.date()}, Vége: {last_day.date()}")
    
                    # Következő hónapra lépés
                    current = next_month
    
                    print("FIRST DAY:   ",first_day.strftime("%Y-%m"))
                    start=first_day.strftime("%Y-%m-%d")
                    # start=datetime.strptime(first_day,"%Y-%m-%d")
                    # print(type(start))
                    # end=datetime.strptime(last_day,"%Y-%m-%d")
                    end=last_day.strftime("%Y-%m-%d")
                    weekends, holidays, holiday_dates, all_days = count_weekends_and_holidays(start, end)
                    
                    # print(f"Hétvégék száma: {weekends}")
                    # print(f"Munkaszüneti napok száma: {holidays}")
                    # print("Munkaszüneti napok:")
                    # for date in holiday_dates:
                        # print(date)
                    # resppp,small_percentage, big_percentage, resource_usage, resource_usage_ = get_allocation(session, weekends, holidays, all_days, start, end)
                    # print(resppp)
                    seq_payload = json.dumps({
                        "filterCriteria": f"Laboratory#laboratoryId = 'L048' AND Allocation#start > '{start}' AND Allocation#end < '{end}' AND Allocation#allocationType !=''",
                        "maxResults":1024,
                        "resultFields":
                        [
                            {"fieldId": "Allocation#end","fieldAlias":"end"},
                            {"fieldId": "Allocation#start","fieldAlias":"start"},
                            {"fieldId": "TestInstance#actualStart", "fieldAlias": "actualStart"},
                            {"fieldId": "TestInstance#actualEnd", "fieldAlias": "actualEnd"},
                            {"fieldId": "Allocation#allocationType","fieldAlias":"type"},
                            {"fieldId": "Allocation#resourceName","fieldAlias":"allocationResourceName"},
                            {"fieldId": "Resource#resourceName","fieldAlias":"resourceName"},
                            {"fieldId": "Laboratory#laboratoryName","fieldAlias":"laboratoryName"},
                            {"fieldId": "Allocation#testInstanceId","fieldAlias":"testInstanceId"},
                        ]

                    })
                    print(seq_payload)
                    response = session.post(base_url+allocation_url, data=seq_payload,  headers=headers_list, cookies=session.cookies)

                    all_day = calculate_days(start, end)
                    working_days = all_day - all_days
                    
                    this_month = datetime.strptime(start, "%Y-%m-%d").strftime("%Y-%m")
                    
                    data = json.loads(response.text)
                    print(data)

                    # Csoportosítás resourceName szerint
                    resource_intervals = {}
                    for entry in data:
                        print("ENRTY: ",entry)
                        
                        if entry["actualStart"] == "" or entry["actualEnd"] == "":
                            print("Start: ",entry["start"])
                            start_dt = datetime.fromisoformat(entry["start"])
                            end_dt = datetime.fromisoformat(entry["end"])
                        else:
                            print("actualStart: ",entry["actualStart"])
                            start_dt = datetime.fromisoformat(entry["actualStart"])
                            end_dt = datetime.fromisoformat(entry["actualEnd"])
                        resource = entry["resourceName"]
                        # start_dt = datetime.fromisoformat(entry["actualStart"])
                        # end_dt = datetime.fromisoformat(entry["actualEnd"])
                        allocation_type = entry["type"]
                        resource_intervals.setdefault(resource, []).append((allocation_type, start_dt, end_dt))
                    # print(resource_intervals)

                    resource_usage = {}
                    
                    resource_usage_ = {}
                    
                    print(resource_intervals.items())

                    for resource, intervals in resource_intervals.items():
                        print("RESOURCE TO CHECK: ",resource)
                        resource_group_usage_by_status = {}
                        # print("INTERVALS: ", intervals)
                        merged_intervals , merged_by_status= merge_intervals(intervals)
                        total_used_days = 0
                        total_used_days_ = 0
                        # print("MERGED_BY_STATUS: ", merged_by_status)
                        for status_type in merged_by_status:
                            total_used_days_ = 0
                            # print("STATUS: ", status_type)
                            for allocation_type_, start_dt_, end_dt_ in merged_by_status[status_type]:
                                if status_type != allocation_type_:
                                    print("error :", status_type," nnn", allocation_type_)
                                usage_days_ = calculate_days(start_dt_.strftime("%Y-%m-%d"), end_dt_.strftime("%Y-%m-%d"))
                                _, _, _, free_days_ = count_weekends_and_holidays(start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
                                total_used_days_ += usage_days_ - free_days_
                            #0
                            usage_percentage_ = (total_used_days_ / working_days) * 100
                            # print("type:", status_type)
                            # print("total_used_days: ",total_used_days_)
                            resource_group_usage_by_status[status_type] = {
                                "used days": total_used_days_,
                                "percentage": usage_percentage_,
                                "worked days": working_days,
                                "weekends": weekends,
                                "holidays": holidays,
                                "actual_month" : this_month,
                                "type" : status_type
                            }
                        resource_usage_[resource] = [resource_group_usage_by_status]
                        
                        for allocation_type, start_dt, end_dt in merged_intervals:
                            usage_days = calculate_days(start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
                            _, _, _, free_days = count_weekends_and_holidays(start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
                            total_used_days += usage_days - free_days
                        #0
                        usage_percentage = (total_used_days / working_days) * 100

                        resource_usage[resource] = {
                            "used days": total_used_days,
                            "percentage": usage_percentage,
                            "worked days": working_days,
                            "weekends": weekends,
                            "holidays": holidays,
                            "actual_month" : this_month,
                            "type" : allocation_type
                        }
                    if resource_usage.get("SMALL noise chamber", {}) == {}:
                        resource_usage_["SMALL noise chamber"] = {
                            "used days": total_used_days_,
                            "percentage": 0,
                            "worked days": 0,
                            "weekends": weekends,
                            "holidays": holidays,
                            "actual_month" : this_month,
                            "type" : 'none'
                        },
                        resource_usage["SMALL noise chamber"] = {
                            "used days": total_used_days,
                            "percentage": 0,
                            "worked days": 0,
                            "weekends": weekends,
                            "holidays": holidays,
                            "actual_month" : this_month,
                            "type" : allocation_type
                        }
                    if resource_usage.get("BIG noise chamber", {}) == {}:
                        resource_usage_["BIG noise chamber"] = {
                            "used days": total_used_days_,
                            "percentage": 0,
                            "worked days": 0,
                            "weekends": weekends,
                            "holidays": holidays,
                            "actual_month" : this_month,
                            "type" : 'none'
                        },
                        resource_usage["BIG noise chamber"] = {
                            "used days": total_used_days,
                            "percentage": 0,
                            "worked days": 0,
                            "weekends": weekends,
                            "holidays": holidays,
                            "actual_month" : this_month,
                            "type" : allocation_type
                        }
                    small_percentage = resource_usage.get("SMALL noise chamber", {}).get("percentage", 0)
                    big_percentage = resource_usage.get("BIG noise chamber", {}).get("percentage", 0)

                    print(json.dumps(resource_usage_, indent=2))
                    print("Small chamber: {}%, Big chamber: {}%".format(small_percentage, big_percentage))
                    # print(small_percentage, big_percentage)
                   
                                        
                    
                    # Adatok hozzáadása a megfelelő kamrához
                    all_resource_usages["BIG noise chamber"].append(resource_usage["BIG noise chamber"])
                    all_resource_usages["SMALL noise chamber"].append(resource_usage["SMALL noise chamber"])
                    
                    # print("RESOURCE USAGE:", resource_usage_)
                    # Adatok hozzáadása a megfelelő kamrához
                    all_resource_usages_["BIG noise chamber"].append(resource_usage_["BIG noise chamber"])
                    all_resource_usages_["SMALL noise chamber"].append(resource_usage_["SMALL noise chamber"])
                    
                print(json.dumps(all_resource_usages_, indent=2))
                # Plot combined usage
                plot_resource_usage_(all_resource_usages_, combined=True)
                plot_resource_usage(all_resource_usages, combined=False)
                plot_resource_usage(all_resource_usages, combined=True)
            except KeyboardInterrupt:
                exit()

