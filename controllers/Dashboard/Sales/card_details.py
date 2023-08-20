import pandas as pd
from flask import jsonify

def CardDetails_level(office_id,from_date,to_date,level,cnxn):
    df = pd.read_sql_query(
        f"""
WITH cte_org AS (
    SELECT
        ofs.OfficeId,
        ofs.MasterOfficeId,
        ofs.OfficeTypeId,
        ofs.OfficeName,
        mo.OfficeName AS MasterOfficeName,
        0 AS Level,
        ofs.OfficeAddress,
        ofs.RegisteredAddress,
        ofs.OfficeContactNo,
        ofs.OfficeEmail,
        ofs.GSTNumber,
        ofs.IsActive,
        ofs.Latitude,
        ofs.Longitude,
        ofs.GstTypeId
    FROM Office ofs
    LEFT JOIN Office mo ON mo.OfficeId = ofs.MasterOfficeId
    WHERE ofs.OfficeId = '{office_id}'

    UNION ALL

    SELECT
        e.OfficeId,
        e.MasterOfficeId,
        e.OfficeTypeId,
        e.OfficeName,
        o.OfficeName AS MasterOfficeName,
        Level + 1 AS Level,
        e.OfficeAddress,
        e.RegisteredAddress,
        e.OfficeContactNo,
        e.OfficeEmail,
        e.GSTNumber,
        e.IsActive,
        e.Latitude,
        e.Longitude,
        e.GstTypeId
    FROM Office e
    INNER JOIN cte_org o ON o.OfficeId = e.MasterOfficeId
)

SELECT
    ct.IsActive,
    ct.Level as level,
    ct.MasterOfficeId As masterOfficeId,
    ct.OfficeId As officeId,
    ct.OfficeName As officeName,
    ot.OfficeTypeName As officeType,
	S.totalIncome As totalIncome,
	S.incomeCount As incomeCount,
	E.totalExpense As totalExpense,
	E.expenseCount As expenseCount,
    ANR.Name As Name
	
FROM cte_org ct
LEFT OUTER JOIN OfficeType ot ON ct.OfficeTypeId = ot.OfficeTypeId

Left Outer join
(
Select SUM(Total) As totalIncome,Count(Total) As incomeCount,OfficeId
From Sales
Where
IsDeleted=0 And
InvoiceDate>='{from_date}' AND InvoiceDate<='{to_date}'
Group By
OfficeId
)S On ct.officeId=S.OfficeId 

Left Outer join
(
Select officeId,SUM(Amount) As totalExpense,Count(Amount) As expenseCount
From Expense
Where
VoucherDate>='{from_date}' AND VoucherDate<='{to_date}'
Group By
officeId
)E On ct.officeId=E.OfficeId

Left Join
UserOfficeMapper UM ON ct.OfficeId=UM.OfficeId

Left Join
AspNetUserRoles ANUR ON ANUR.userId=UM.userId

Left Join
AspNetRoles ANR ON ANR.Id=ANUR.RoleId

WHERE
    ct.IsActive=1 and ({level} < 0 OR ct.Level <= {level}) 
""",
        cnxn,
    )

    return df

def CardDetails(office_id,is_admin,cnxn):

    today_date = pd.to_datetime('today').date()
    previous_date = today_date
    previous_7_date = today_date - pd.DateOffset(days=7)
    df = CardDetails_level(office_id,previous_7_date,previous_date,-1,cnxn)
    
    if(is_admin==1):
        #df = CardDetails_level(office_id,previous_7_date,previous_date,-1,cnxn)
        df1=df
        copy_df=df1.copy()
        df1=df1[~((df1['Name']=="SuperAdmin")|(df1["officeId"].str.lower()==office_id.lower())|(df1["level"]>1))]
        df1.fillna(0,inplace=True)
        Sales_Expense_df=df1[["officeId","officeType"]].drop_duplicates()
        officeCount=Sales_Expense_df['officeType'].value_counts().to_dict()
        officeCount=pd.DataFrame.from_dict(officeCount,orient='index',columns=['officeCount'])
        officeCount.reset_index(inplace=True,drop=False)
        officeCount.rename(columns={'index':'officeTypeName'},inplace=True)

        User_df=df1[["Name","officeId"]]
        User_df=User_df[~((df1["Name"]==0)|(df["officeId"]==0))]
        userCount=User_df["Name"].value_counts().to_dict()
        userCount=pd.DataFrame.from_dict(userCount,orient='index',columns=["userCount"])
        userCount.reset_index(inplace=True,drop=False)
        userCount.rename(columns={'index':'roleName'},inplace=True)
        
    else:
        df2 = df[df["level"]==0]
        copy_df=df2.copy()
        df2=df2[~(df2['Name']=="SuperAdmin")]
        df2.fillna(0,inplace=True)
        Sales_Expense_df=df2[["officeId","officeType"]].drop_duplicates()
        officeCount=Sales_Expense_df['officeType'].value_counts().to_dict()
        officeCount=pd.DataFrame.from_dict(officeCount,orient='index',columns=['officeCount'])
        officeCount.reset_index(inplace=True,drop=False)
        officeCount.rename(columns={'index':'officeTypeName'},inplace=True)

        User_df=df2["Name"]
        userCount=User_df.value_counts().to_dict()
        userCount=pd.DataFrame.from_dict(userCount,orient='index',columns=["userCount"])
        userCount.reset_index(inplace=True,drop=False)
        userCount.rename(columns={'index':'roleName'},inplace=True)
    
    copy_df=copy_df[["officeId","totalIncome","incomeCount","totalExpense","expenseCount"]].drop_duplicates()
    
    Current_df=CardDetails_level(office_id,previous_7_date,previous_date,-1,cnxn)
    print(Current_df)
    incomeDetailsCurrentDay_total=0
    incomeDetailsCurrentDay_count=0
    expenseDetailsCurrentDay_total=0
    expenseDetailsCurrentDay_count=0
    if(len(Current_df)>0):
        incomeDetailsCurrentDay_total=Current_df["totalIncome"].sum()
        incomeDetailsCurrentDay_count=Current_df["incomeCount"].sum()
        expenseDetailsCurrentDay_total=Current_df["totalExpense"].sum()
        expenseDetailsCurrentDay_count=Current_df["expenseCount"].sum()

    return jsonify(
        {
            "userCount":userCount.to_dict(orient="records"),
            "officeCount":officeCount.to_dict(orient="records"),
            "incomeDetails":{
                "total":int(copy_df["totalIncome"].sum()),
                "count":int(copy_df["incomeCount"].sum())
            },
            "expenseDetails":{
                "total":int(copy_df["totalExpense"].sum()),
                "count":int(copy_df["expenseCount"].sum())
            },
            "incomeDetailsCurrentDay":{
                "total":incomeDetailsCurrentDay_total,
                "count":incomeDetailsCurrentDay_count
            },
            "expenseDetailsCurrentDay":{
                "total":expenseDetailsCurrentDay_total,
                "count":expenseDetailsCurrentDay_count
            }
        }
    )
