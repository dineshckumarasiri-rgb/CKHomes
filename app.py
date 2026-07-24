from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from uuid import uuid4

import pandas as pd
import plotly.express as px
import streamlit as st

from services.google_sheet import GoogleSheetService, StorageError

st.set_page_config(page_title="CEEKAY Homes", page_icon="🏠", layout="wide", initial_sidebar_state="expanded")

CSS = """
<style>
.block-container{
    padding-top:1.25rem;
    max-width:1500px;
}

.stApp{
    background:#f5f7fb;
}

/* Sidebar background */
section[data-testid="stSidebar"]{
    background:#0f172a !important;
}

/* Sidebar text */
section[data-testid="stSidebar"] *{
    color:#f8fafc !important;
}

/* Sidebar secondary text */
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
section[data-testid="stSidebar"] p{
    color:#cbd5e1 !important;
}

/* Navigation radio labels */
section[data-testid="stSidebar"] div[role="radiogroup"] label{
    color:#f8fafc !important;
    border-radius:10px;
    padding:4px 8px;
}

/* Selected navigation item */
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked){
    background:#1e293b !important;
}

/* Radio circles */
section[data-testid="stSidebar"] div[role="radiogroup"] svg{
    color:#f8fafc !important;
    fill:#f8fafc !important;
}

/* Sidebar divider */
section[data-testid="stSidebar"] hr{
    border-color:#334155 !important;
}

/* Logout button */
section[data-testid="stSidebar"] .stButton > button{
    background:#f8fafc !important;
    color:#0f172a !important;
    border:none !important;
}

section[data-testid="stSidebar"] .stButton > button *{
    color:#0f172a !important;
}

.brand{
    font-size:1.35rem;
    font-weight:800;
    letter-spacing:.02em;
    color:#ffffff !important;
}

.muted{
    color:#64748b;
}

.card{
    background:white;
    border:1px solid #e5e7eb;
    border-radius:18px;
    padding:18px;
    box-shadow:0 8px 24px rgba(15,23,42,.05);
}

.kpi{
    font-size:2rem;
    font-weight:800;
    margin-top:6px;
}

.label{
    font-size:.85rem;
    color:#64748b;
    font-weight:600;
}

.hero{
    background:linear-gradient(135deg,#0f172a,#1f2937);
    color:white;
    padding:24px;
    border-radius:22px;
    margin-bottom:18px;
}

div[data-testid="stMetric"]{
    background:white;
    border:1px solid #e5e7eb;
    padding:14px;
    border-radius:16px;
}

.stButton > button{
    border-radius:10px;
    font-weight:700;
}

.stTextInput input,
.stNumberInput input,
.stSelectbox div[data-baseweb="select"] > div{
    border-radius:10px;
}

/* Premium single-card login page */
.login-panel{
    text-align:center;
    padding:4px 6px 0;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.login-panel){
    max-width:520px;
    margin:5vh auto 0;
    background:#ffffff;
    border:1px solid #e2e8f0 !important;
    border-radius:24px !important;
    padding:30px 30px 24px !important;
    box-shadow:0 20px 50px rgba(15,23,42,.12);
}

.login-logo{
    width:64px;
    height:64px;
    margin:0 auto 16px;
    display:flex;
    align-items:center;
    justify-content:center;
    border-radius:18px;
    background:linear-gradient(135deg,#0f172a,#334155);
    font-size:30px;
    color:#fff;
}

.login-brand{
    text-align:center;
    font-size:1.05rem;
    font-weight:800;
    letter-spacing:.08em;
    color:#0f172a;
    margin-bottom:8px;
}

.login-title{
    text-align:center;
    font-size:1.9rem;
    font-weight:800;
    color:#0f172a;
    margin:0;
}

.login-subtitle{
    text-align:center;
    color:#64748b;
    margin:8px 0 24px;
    font-size:.95rem;
}

.login-footer{
    text-align:center;
    color:#94a3b8;
    font-size:.78rem;
    margin-top:16px;
}

div[data-testid="stForm"]{
    border:0 !important;
    padding:0 !important;
    background:transparent !important;
}

div[data-testid="stForm"] .stTextInput label{
    color:#334155 !important;
    font-weight:600 !important;
}

div[data-testid="stForm"] .stTextInput input{
    min-height:48px;
    background:#f8fafc;
    border:1px solid #cbd5e1;
}

div[data-testid="stForm"] .stTextInput input:focus{
    border-color:#0f172a;
    box-shadow:0 0 0 1px #0f172a;
}

div[data-testid="stForm"] .stFormSubmitButton>button{
    min-height:48px;
    width:100%;
    background:linear-gradient(135deg,#0f172a,#334155) !important;
    color:#fff !important;
    border:none !important;
    border-radius:12px !important;
    font-weight:700 !important;
    margin-top:8px;
}

div[data-testid="stForm"] .stFormSubmitButton>button:hover{
    transform:translateY(-1px);
    box-shadow:0 10px 22px rgba(15,23,42,.18);
}

div[data-testid="stForm"] .stFormSubmitButton>button *{
    color:#fff !important;
}

</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def now(): return datetime.now().isoformat(timespec="seconds")
def uid(prefix): return f"{prefix}-{uuid4().hex[:8].upper()}"
def money(v):
    try: return float(v or 0)
    except Exception: return 0.0

def active(rows): return [r for r in rows if str(r.get("status","Active")) not in {"Deleted","Void","Cancelled"}]

@st.cache_resource
def get_service():
    if "gcp_service_account" not in st.secrets:
        raise StorageError("Google credentials are missing from Streamlit Secrets.")
    return GoogleSheetService(
        spreadsheet_name=st.secrets.get("GOOGLE_SHEET_NAME", "CEEKAY Homes Management"),
        credentials_info=dict(st.secrets["gcp_service_account"]),
        cache_ttl=60,
    )


def rerun_ok(msg):
    st.session_state["_success_message"] = msg
    st.cache_data.clear()
    st.rerun()


def login():
    _, c, _ = st.columns([1, 1.15, 1])
    with c:
        with st.container(border=True):
            st.markdown(
                """
                <div class='login-panel'>
                    <div class='login-logo'>🏠</div>
                    <div class='login-brand'>CEEKAY HOMES</div>
                    <h1 class='login-title'>Hostel Management</h1>
                    <p class='login-subtitle'>Secure access to your management console</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.form("login"):
                u = st.text_input("Username", placeholder="Enter your username")
                p = st.text_input("Password", type="password", placeholder="Enter your password")
                ok = st.form_submit_button("Sign in", use_container_width=True)

            if ok:
                if u == st.secrets.get("ADMIN_USERNAME","admin") and p == st.secrets.get("ADMIN_PASSWORD","admin123"):
                    st.session_state.auth = True
                    st.session_state.user = u
                    st.rerun()
                else:
                    st.error("Invalid username or password")

            st.markdown(
                "<div class='login-footer'>© 2026 CEEKAY Homes · Secure cloud administration</div>",
                unsafe_allow_html=True,
            )

if not st.session_state.get("auth"):
    login(); st.stop()

try:
    svc = get_service()
    svc.initialize()
except Exception as e:
    st.error(str(e)); st.info("Add your Google service account details in Streamlit Cloud → App settings → Secrets, then restart the app."); st.stop()

if st.session_state.get("_success_message"):
    st.success(st.session_state.pop("_success_message"))

with st.sidebar:
    st.markdown("<div class='brand'>🏠 CEEKAY Homes</div><p style='color:#94a3b8'>Management Console</p>", unsafe_allow_html=True)
    page = st.radio("Navigation", ["Dashboard","Hostel","Students","Payments","Deposits","Expenses","Assets","Reports","Settings"], label_visibility="collapsed")
    st.divider()
    st.caption(f"Signed in as {st.session_state.get('user','admin')}")
    if st.button("Log out", use_container_width=True):
        st.session_state.clear(); st.rerun()


def header(title, subtitle=""):
    st.markdown(f"<div class='hero'><h1>{title}</h1><p>{subtitle}</p></div>", unsafe_allow_html=True)


def df(rows, cols=None):
    d = pd.DataFrame(rows)
    if cols and not d.empty: d = d[[c for c in cols if c in d.columns]]
    return d

if page == "Dashboard":
    header("Dashboard", "A live overview of hostel operations")
    students = svc.get_table("Students"); beds = svc.get_table("Beds")
    payments = active(svc.get_table("Payments")); costs = active(svc.get_table("Costs")); deps = svc.get_table("StudentDeposits")
    active_students = [x for x in students if x.get("student_status","Active") == "Active"]
    revenue = sum(money(x.get("amount")) for x in payments); expense = sum(money(x.get("amount")) for x in costs)
    cols = st.columns(5)
    vals = [("Active Students",len(active_students)),("Available Beds",sum(1 for x in beds if x.get("status","Available")=="Available")),("Revenue",f"LKR {revenue:,.0f}"),("Expenses",f"LKR {expense:,.0f}"),("Net Profit",f"LKR {revenue-expense:,.0f}")]
    for c,(a,b) in zip(cols,vals): c.metric(a,b)
    monthly = {}
    for r in payments:
        k=str(r.get("payment_date",""))[:7] or "Unknown"; monthly.setdefault(k,{"month":k,"Revenue":0,"Expenses":0}); monthly[k]["Revenue"] += money(r.get("amount"))
    for r in costs:
        k=str(r.get("cost_date",""))[:7] or "Unknown"; monthly.setdefault(k,{"month":k,"Revenue":0,"Expenses":0}); monthly[k]["Expenses"] += money(r.get("amount"))
    c1,c2=st.columns([1.5,1])
    with c1:
        st.subheader("Monthly performance")
        chart=pd.DataFrame([monthly[k] for k in sorted(monthly)[-12:]])
        if not chart.empty: st.plotly_chart(px.bar(chart,x="month",y=["Revenue","Expenses"],barmode="group"),use_container_width=True)
        else: st.info("No finance data yet")
    with c2:
        st.subheader("Occupancy")
        occ=sum(1 for x in beds if x.get("status")=="Occupied"); ava=sum(1 for x in beds if x.get("status","Available")=="Available")
        st.plotly_chart(px.pie(values=[occ,ava],names=["Occupied","Available"],hole=.62),use_container_width=True)

elif page == "Hostel":
    header("Hostel Management", "Manage blocks, rooms and beds")
    t1,t2,t3=st.tabs(["Blocks","Rooms","Beds"])
    with t1:
        with st.expander("Add block", expanded=False):
            with st.form("add_block", clear_on_submit=True):
                a,b=st.columns(2); name=a.text_input("Block name*"); floors=b.number_input("Floors",1,20,1); address=st.text_area("Address")
                if st.form_submit_button("Save block"):
                    if not name: st.error("Block name is required")
                    else:
                        svc.add_record("HostelBlocks",{"block_id":uid("BLK"),"block_name":name.strip(),"address":address,"floors":floors,"status":"Active","created_at":now()}); rerun_ok("Block added")
        blocks=svc.get_table("HostelBlocks"); st.dataframe(df(blocks,["block_id","block_name","address","floors","status"]),use_container_width=True,hide_index=True)
        if blocks:
            bid=st.selectbox("Delete block",[x["block_id"] for x in blocks],format_func=lambda x:next((b["block_name"] for b in blocks if b["block_id"]==x),x))
            if st.button("Delete selected block"):
                if any(str(r.get("block_id"))==str(bid) for r in svc.get_table("Rooms")): st.error("Delete its rooms first")
                else: svc.delete_record("HostelBlocks","block_id",bid); rerun_ok("Block deleted")
    with t2:
        blocks=svc.get_table("HostelBlocks")
        with st.expander("Add room"):
            with st.form("add_room", clear_on_submit=True):
                block=st.selectbox("Block*",[b["block_id"] for b in blocks],format_func=lambda x:next((b["block_name"] for b in blocks if b["block_id"]==x),x)) if blocks else None
                c1,c2,c3,c4=st.columns(4); room_no=c1.text_input("Room no*"); room_type=c2.selectbox("Type",["Standard","Shared","Single","Other"]); cap=c3.number_input("Capacity",1,20,1); charge=c4.number_input("Monthly charge",0.0,1000000.0,0.0)
                if st.form_submit_button("Save room"):
                    if not block or not room_no: st.error("Block and room number are required")
                    else:
                        bn=next(b["block_name"] for b in blocks if b["block_id"]==block); rid=uid("ROM")
                        svc.add_record("Rooms",{"room_id":rid,"block_id":block,"block_name":bn,"room_no":room_no,"room_type":room_type,"capacity":cap,"monthly_charge":charge,"status":"Active","created_at":now()})
                        for i in range(1,int(cap)+1): svc.add_record("Beds",{"bed_id":uid("BED"),"room_id":rid,"block_id":block,"block_name":bn,"room_no":room_no,"bed_no":str(i),"status":"Available","student_id":"","student_name":"","created_at":now(),"updated_at":now()})
                        rerun_ok("Room and beds added")
        rooms=svc.get_table("Rooms"); st.dataframe(df(rooms,["room_id","block_name","room_no","room_type","capacity","monthly_charge","status"]),use_container_width=True,hide_index=True)
    with t3:
        beds=svc.get_table("Beds"); st.dataframe(df(beds,["bed_id","block_name","room_no","bed_no","status","student_id","student_name"]),use_container_width=True,hide_index=True)
        if beds:
            bedid=st.selectbox("Select bed",[b["bed_id"] for b in beds],format_func=lambda x:next((f"{b['block_name']} / Room {b['room_no']} / Bed {b['bed_no']}" for b in beds if b['bed_id']==x),x))
            status=st.selectbox("Set status",["Available","Maintenance","Unavailable"])
            if st.button("Update bed status"):
                bed=next(b for b in beds if b["bed_id"]==bedid)
                if bed.get("student_id"): st.error("Occupied beds cannot be manually changed")
                else: svc.update_record("Beds","bed_id",bedid,{"status":status,"updated_at":now()}); rerun_ok("Bed updated")

elif page == "Students":
    header("Student Management", "Register, edit, transfer and withdraw students")
    tabs=st.tabs(["Directory","Add Student","Edit / Transfer / Withdraw"])
    students=svc.get_table("Students")
    with tabs[0]:
        q=st.text_input("Search students")
        rows=[s for s in students if not q or q.lower() in " ".join(str(v) for v in s.values()).lower()]
        st.dataframe(df(rows,["student_id","full_name","mobile","university","hostel_block","room_no","bed_no","monthly_fee","student_status"]),use_container_width=True,hide_index=True)
    with tabs[1]:
        beds=[b for b in svc.get_table("Beds") if b.get("status","Available")=="Available"]
        with st.form("student_add", clear_on_submit=True):
            c1,c2,c3=st.columns(3); full=c1.text_input("Full name*"); nic=c2.text_input("NIC"); mobile=c3.text_input("Mobile*")
            c4,c5,c6=st.columns(3); email=c4.text_input("Email"); dob=c5.date_input("Date of birth",value=date(2000,1,1)); gender=c6.selectbox("Gender",["Female","Male","Other"])
            address=st.text_area("Address"); c7,c8,c9=st.columns(3); university=c7.text_input("University"); degree=c8.text_input("Degree"); reg=c9.text_input("Registration no")
            c10,c11,c12=st.columns(3); guardian=c10.text_input("Guardian name"); gmobile=c11.text_input("Guardian mobile"); joining=c12.date_input("Joining date")
            bedid=st.selectbox("Assign available bed",[""]+[b["bed_id"] for b in beds],format_func=lambda x:"Not assigned" if not x else next((f"{b['block_name']} / Room {b['room_no']} / Bed {b['bed_no']}" for b in beds if b['bed_id']==x),x))
            dep=st.number_input("Required deposit",0.0,1000000.0,0.0)
            if st.form_submit_button("Add student"):
                if not full or not mobile: st.error("Full name and mobile are required")
                else:
                    sid=svc.next_student_id(); bed=next((b for b in beds if b["bed_id"]==bedid),{})
                    room=svc.find_one("Rooms","room_id",str(bed.get("room_id",""))) or {}
                    record={k:"" for k in svc.HEADERS["Students"]}; record.update({"student_id":sid,"full_name":full.strip().upper(),"name_with_initials":full.strip().upper(),"nic":nic.strip().upper(),"date_of_birth":dob.isoformat(),"gender":gender.upper(),"nationality":"SRI LANKAN","mobile":mobile.strip(),"whatsapp":mobile.strip(),"email":email.strip().lower(),"address":address.strip().upper(),"guardian_name":guardian.strip().upper(),"guardian_mobile":gmobile.strip(),"university":university.strip().upper(),"degree":degree.strip().upper(),"university_reg_no":reg.strip().upper(),"joining_date":joining.isoformat(),"hostel_block":str(bed.get("block_name","")).upper(),"block_id":bed.get("block_id",""),"room_no":bed.get("room_no",""),"room_id":bed.get("room_id",""),"bed_no":bed.get("bed_no",""),"bed_id":bedid,"monthly_fee":room.get("monthly_charge",0),"student_status":"Active","approved_at":now()})
                    svc.add_record("Students",record)
                    svc.add_record("StudentDeposits",{"deposit_id":uid("DEP"),"student_id":sid,"student_name":full.strip().upper(),"required_amount":dep,"received_amount":0,"status":"Not Paid","total_deductions":0,"refundable_amount":0,"refunded_amount":0,"balance_to_refund":0,"updated_at":now()})
                    if bedid:
                        svc.update_record("Beds","bed_id",bedid,{"status":"Occupied","student_id":sid,"student_name":full.strip().upper(),"updated_at":now()})
                        svc.add_record("RoomAssignments",{"assignment_id":uid("ASN"),"student_id":sid,"student_name":full.strip().upper(),"block_id":bed.get("block_id"),"block_name":bed.get("block_name"),"room_id":bed.get("room_id"),"room_no":bed.get("room_no"),"bed_id":bedid,"bed_no":bed.get("bed_no"),"start_date":joining.isoformat(),"end_date":"","status":"Active","created_at":now()})
                    rerun_ok(f"Student added: {sid}")
    with tabs[2]:
        if not students: st.info("No students yet")
        else:
            sid=st.selectbox("Select student",[s["student_id"] for s in students],format_func=lambda x:next((f"{x} — {s['full_name']}" for s in students if s['student_id']==x),x)); s=next(x for x in students if x["student_id"]==sid)
            st.write(f"**Current room:** {s.get('hostel_block','')} / {s.get('room_no','')} / Bed {s.get('bed_no','')}")
            with st.form("edit_student", clear_on_submit=True):
                a,b,c=st.columns(3); full=a.text_input("Full name",s.get("full_name","")); mobile=b.text_input("Mobile",s.get("mobile","")); email=c.text_input("Email",s.get("email","")); address=st.text_area("Address",s.get("address",""))
                if st.form_submit_button("Save student changes"):
                    svc.update_record("Students","student_id",sid,{"full_name":full.strip().upper(),"name_with_initials":full.strip().upper(),"mobile":mobile.strip(),"whatsapp":mobile.strip(),"email":email.strip().lower(),"address":address.strip().upper()}); rerun_ok("Student updated")
            available=[b for b in svc.get_table("Beds") if b.get("status","Available")=="Available"]
            with st.form("transfer", clear_on_submit=True):
                newbed=st.selectbox("Transfer to",[b["bed_id"] for b in available],format_func=lambda x:next((f"{b['block_name']} / Room {b['room_no']} / Bed {b['bed_no']}" for b in available if b['bed_id']==x),x)) if available else None
                tdate=st.date_input("Transfer date")
                if st.form_submit_button("Change room"):
                    if not newbed: st.error("No available bed")
                    else:
                        nb=next(b for b in available if b["bed_id"]==newbed); room=svc.find_one("Rooms","room_id",nb["room_id"]) or {}
                        old=s.get("bed_id");
                        if old: svc.update_record("Beds","bed_id",old,{"status":"Available","student_id":"","student_name":"","updated_at":now()})
                        for a in svc.get_table("RoomAssignments"):
                            if a.get("student_id")==sid and a.get("status")=="Active": svc.update_record("RoomAssignments","assignment_id",a["assignment_id"],{"status":"Completed","end_date":tdate.isoformat()})
                        svc.update_record("Beds","bed_id",newbed,{"status":"Occupied","student_id":sid,"student_name":s.get("full_name"),"updated_at":now()})
                        svc.update_record("Students","student_id",sid,{"hostel_block":nb.get("block_name"),"block_id":nb.get("block_id"),"room_no":nb.get("room_no"),"room_id":nb.get("room_id"),"bed_no":nb.get("bed_no"),"bed_id":newbed,"monthly_fee":room.get("monthly_charge",0)})
                        svc.add_record("RoomAssignments",{"assignment_id":uid("ASN"),"student_id":sid,"student_name":s.get("full_name"),"block_id":nb.get("block_id"),"block_name":nb.get("block_name"),"room_id":nb.get("room_id"),"room_no":nb.get("room_no"),"bed_id":newbed,"bed_no":nb.get("bed_no"),"start_date":tdate.isoformat(),"end_date":"","status":"Active","created_at":now()}); rerun_ok("Room changed")
            with st.form("withdraw", clear_on_submit=True):
                student_payments = [
                    p for p in active(svc.get_table("Payments"))
                    if str(p.get("student_id","")) == str(sid)
                ]
                student_payments.sort(
                    key=lambda p: (
                        str(p.get("payment_date","")),
                        str(p.get("created_at",""))
                    )
                )
                last_payment = student_payments[-1] if student_payments else {}
                last_paid_amount = money(last_payment.get("amount")) if last_payment else money(s.get("monthly_fee"))
                last_paid_month = str(last_payment.get("month","")) if last_payment else ""

                st.number_input("Last paid amount", value=last_paid_amount, disabled=True)
                if last_paid_month:
                    st.caption(f"Last paid month: {last_paid_month}")
                st.caption(
                    f"Room details will be retained: "
                    f"{s.get('hostel_block','')} / Room {s.get('room_no','')} / Bed {s.get('bed_no','')}"
                )

                wd=st.date_input("Withdrawal date"); reason=st.text_area("Reason")
                if st.form_submit_button("Withdraw student"):
                    if s.get("bed_id"):
                        svc.update_record(
                            "Beds",
                            "bed_id",
                            s["bed_id"],
                            {
                                "status":"Available",
                                "student_id":"",
                                "student_name":"",
                                "updated_at":now()
                            }
                        )

                    svc.update_record(
                        "Students",
                        "student_id",
                        sid,
                        {
                            "student_status":"Withdrawn",
                            "withdrawal_date":wd.isoformat(),
                            "withdrawal_reason":reason.strip().upper(),
                            "monthly_fee":last_paid_amount
                        }
                    )

                    for assignment in svc.get_table("RoomAssignments"):
                        if assignment.get("student_id")==sid and assignment.get("status")=="Active":
                            svc.update_record(
                                "RoomAssignments",
                                "assignment_id",
                                assignment["assignment_id"],
                                {
                                    "status":"Completed",
                                    "end_date":wd.isoformat()
                                }
                            )

                    svc.add_record(
                        "Withdrawals",
                        {
                            "withdrawal_id":uid("WDR"),
                            "student_id":sid,
                            "student_name":s.get("full_name"),
                            "boarding_fee":last_paid_amount,
                            "withdrawal_date":wd.isoformat(),
                            "reason":reason.strip().upper(),
                            "deposit_status":"Pending",
                            "created_by":st.session_state.user,
                            "created_at":now()
                        }
                    )
                    rerun_ok("Student withdrawn")

            st.divider()
            st.subheader("Delete wrongly added student")
            st.caption("Use this only when a student was added by mistake.")

            with st.form("delete_student"):
                confirm_delete = st.checkbox(
                    f"I confirm that I want to permanently delete {s.get('full_name','this student')}"
                )

                if st.form_submit_button("Delete student permanently"):
                    if not confirm_delete:
                        st.error("Please confirm the deletion first.")
                    else:
                        related_payments = [
                            p for p in svc.get_table("Payments")
                            if str(p.get("student_id","")) == str(sid)
                        ]

                        if related_payments:
                            st.error(
                                "This student has payment records and cannot be deleted. "
                                "Please use the withdrawal option instead."
                            )
                        else:
                            if s.get("bed_id"):
                                svc.update_record(
                                    "Beds",
                                    "bed_id",
                                    s["bed_id"],
                                    {
                                        "status":"Available",
                                        "student_id":"",
                                        "student_name":"",
                                        "updated_at":now()
                                    }
                                )

                            for assignment in svc.get_table("RoomAssignments"):
                                if str(assignment.get("student_id","")) == str(sid):
                                    svc.delete_record(
                                        "RoomAssignments",
                                        "assignment_id",
                                        assignment["assignment_id"]
                                    )

                            for deposit in svc.get_table("StudentDeposits"):
                                if str(deposit.get("student_id","")) == str(sid):
                                    svc.delete_record(
                                        "StudentDeposits",
                                        "deposit_id",
                                        deposit["deposit_id"]
                                    )

                            svc.delete_record("Students","student_id",sid)
                            rerun_ok("Student deleted permanently")

elif page == "Payments":
    header("Payments", "Record, edit and delete student payments")
    students=[s for s in svc.get_table("Students") if s.get("student_status","Active")=="Active"]
    with st.expander("Add payment", expanded=True):
        with st.form("pay", clear_on_submit=True):
            sid=st.selectbox("Student",[s["student_id"] for s in students],format_func=lambda x:next((f"{x} — {s['full_name']}" for s in students if s['student_id']==x),x)) if students else None
            c1,c2,c3,c4=st.columns(4); category=c1.selectbox("Category",["Monthly Fee","Registration","Other"]); month=c2.text_input("Month",datetime.now().strftime("%Y-%m")); amount=c3.number_input("Amount",0.0,10000000.0,0.0); pdate=c4.date_input("Payment date")
            c5,c6,c7=st.columns(3); method=c5.selectbox("Method",["Cash","Bank Transfer","Card","Other"]); ref=c6.text_input("Reference no"); receipt=c7.text_input("Receipt no"); remarks=st.text_area("Remarks")
            if st.form_submit_button("Save payment"):
                if not sid or amount<=0: st.error("Student and amount are required")
                else:
                    s=next(x for x in students if x["student_id"]==sid)
                    svc.add_record("Payments",{"payment_id":uid("PAY"),"student_id":sid,"student_name":s["full_name"],"revenue_category":category,"month":month,"amount":amount,"payment_date":pdate.isoformat(),"method":method,"reference_no":ref,"receipt_no":receipt,"block_name":s.get("hostel_block",""),"remarks":remarks,"status":"Active","created_by":st.session_state.user,"created_at":now()}); rerun_ok("Payment added")
    pays=active(svc.get_table("Payments")); st.dataframe(df(pays,["payment_id","payment_date","student_id","student_name","revenue_category","month","amount","method","receipt_no"]),use_container_width=True,hide_index=True)
    if pays:
        pid=st.selectbox("Delete payment",[p["payment_id"] for p in pays],format_func=lambda x:next((f"{x} — {p['student_name']} — LKR {money(p['amount']):,.0f}" for p in pays if p['payment_id']==x),x))
        if st.button("Permanently delete payment"):
            svc.delete_record("Payments","payment_id",pid); rerun_ok("Payment deleted")

elif page == "Deposits":
    header("Deposits", "Receive, deduct and refund student deposits")
    students=svc.get_table("Students"); deposits=svc.get_table("StudentDeposits")
    st.dataframe(df(deposits,["student_id","student_name","required_amount","received_amount","total_deductions","refunded_amount","balance_to_refund","status"]),use_container_width=True,hide_index=True)
    if deposits:
        sid=st.selectbox("Select student deposit",[d["student_id"] for d in deposits],format_func=lambda x:next((f"{x} — {d['student_name']}" for d in deposits if d['student_id']==x),x)); d=next(x for x in deposits if x["student_id"]==sid)
        t1,t2,t3=st.tabs(["Receive","Deduct","Refund"])
        with t1:
            with st.form("receive_dep", clear_on_submit=True):
                amt=st.number_input("Amount received",0.0,10000000.0,0.0); dt=st.date_input("Date",key="rd"); method=st.selectbox("Method",["Cash","Bank Transfer","Other"],key="rm"); ref=st.text_input("Reference",key="rr")
                if st.form_submit_button("Record receipt"):
                    received=money(d.get("received_amount"))+amt; required=money(d.get("required_amount")); status="Paid" if received>=required else "Partially Paid"
                    svc.update_record("StudentDeposits","student_id",sid,{"received_amount":received,"payment_date":dt.isoformat(),"payment_method":method,"payment_reference":ref,"status":status,"refundable_amount":max(0,received-money(d.get("total_deductions"))),"balance_to_refund":max(0,received-money(d.get("total_deductions"))-money(d.get("refunded_amount"))),"updated_at":now()}); rerun_ok("Deposit receipt recorded")
        with t2:
            with st.form("deduct_dep", clear_on_submit=True):
                amt=st.number_input("Deduction amount",0.0,10000000.0,0.0,key="da"); reason=st.text_input("Reason"); dt=st.date_input("Date",key="dd")
                if st.form_submit_button("Add deduction"):
                    svc.add_record("DepositDeductions",{"deduction_id":uid("DED"),"deposit_id":d["deposit_id"],"student_id":sid,"student_name":d["student_name"],"deduction_date":dt.isoformat(),"amount":amt,"reason":reason,"approved_by":st.session_state.user,"created_at":now()})
                    td=money(d.get("total_deductions"))+amt; refundable=max(0,money(d.get("received_amount"))-td); balance=max(0,refundable-money(d.get("refunded_amount")))
                    svc.update_record("StudentDeposits","student_id",sid,{"total_deductions":td,"refundable_amount":refundable,"balance_to_refund":balance,"updated_at":now()}); rerun_ok("Deduction added")
        with t3:
            with st.form("refund_dep", clear_on_submit=True):
                amt=st.number_input("Refund amount",0.0,10000000.0,0.0,key="fa"); dt=st.date_input("Date",key="fd"); method=st.selectbox("Method",["Cash","Bank Transfer","Other"],key="fm"); ref=st.text_input("Reference",key="fr")
                if st.form_submit_button("Record refund"):
                    svc.add_record("DepositRefunds",{"refund_id":uid("REF"),"deposit_id":d["deposit_id"],"student_id":sid,"student_name":d["student_name"],"refund_date":dt.isoformat(),"amount":amt,"method":method,"reference_no":ref,"remarks":"","created_by":st.session_state.user,"created_at":now()})
                    refunded=money(d.get("refunded_amount"))+amt; balance=max(0,money(d.get("refundable_amount"))-refunded); status="Refunded" if balance<=0 else "Partially Refunded"
                    svc.update_record("StudentDeposits","student_id",sid,{"refunded_amount":refunded,"balance_to_refund":balance,"last_refund_date":dt.isoformat(),"status":status,"updated_at":now()}); rerun_ok("Refund recorded")

elif page == "Expenses":
    header("Expenses", "Simple expense management")
    with st.expander("Add expense", expanded=True):
        with st.form("cost", clear_on_submit=True):
            c1,c2,c3=st.columns(3); dt=c1.date_input("Date"); category=c2.selectbox("Category",["Utilities","Maintenance","Supplies","Salary","Other"]); amount=c3.number_input("Amount",0.0,10000000.0,0.0)
            c4,c5,c6=st.columns(3); desc=c4.text_input("Description"); supplier=c5.text_input("Supplier"); method=c6.selectbox("Method",["Cash","Bank Transfer","Card","Other"]); remarks=st.text_area("Remarks")
            if st.form_submit_button("Save expense"):
                svc.add_record("Costs",{"cost_id":uid("CST"),"cost_date":dt.isoformat(),"category":category,"description":desc,"supplier":supplier,"amount":amount,"method":method,"remarks":remarks,"status":"Active","created_by":st.session_state.user,"created_at":now()}); rerun_ok("Expense added")
    costs=active(svc.get_table("Costs")); st.dataframe(df(costs,["cost_id","cost_date","category","description","supplier","amount","method"]),use_container_width=True,hide_index=True)
    if costs:
        cid=st.selectbox("Delete expense",[c["cost_id"] for c in costs]);
        if st.button("Delete selected expense"): svc.delete_record("Costs","cost_id",cid); rerun_ok("Expense deleted")

elif page == "Assets":
    header("Assets", "Track hostel furniture and equipment")
    with st.expander("Add asset", expanded=True):
        with st.form("asset", clear_on_submit=True):
            c1,c2,c3=st.columns(3); name=c1.text_input("Asset name"); category=c2.text_input("Category"); qty=c3.number_input("Quantity",1,10000,1)
            c4,c5,c6=st.columns(3); block=c4.text_input("Block"); room=c5.text_input("Room"); condition=c6.selectbox("Condition",["New","Good","Fair","Damaged"]); value=st.number_input("Purchase value",0.0,10000000.0,0.0)
            if st.form_submit_button("Save asset"):
                svc.add_record("Assets",{"asset_id":uid("AST"),"asset_name":name,"category":category,"quantity":qty,"block_name":block,"room_no":room,"condition":condition,"purchase_value":value,"status":"Active","updated_at":now()}); rerun_ok("Asset added")
    assets=svc.get_table("Assets"); st.dataframe(df(assets),use_container_width=True,hide_index=True)
    if assets:
        aid=st.selectbox("Delete asset",[a["asset_id"] for a in assets]);
        if st.button("Delete selected asset"): svc.delete_record("Assets","asset_id",aid); rerun_ok("Asset deleted")

elif page == "Reports":
    header("Reports", "Filter and export hostel data")
    report=st.selectbox("Report",["Students","Payments","Deposits","Expenses","Beds","Room Assignments","Withdrawals","Assets"])
    map_={"Students":"Students","Payments":"Payments","Deposits":"StudentDeposits","Expenses":"Costs","Beds":"Beds","Room Assignments":"RoomAssignments","Withdrawals":"Withdrawals","Assets":"Assets"}
    rows=svc.get_table(map_[report]); data=df(rows); st.dataframe(data,use_container_width=True,hide_index=True)
    out=BytesIO()
    with pd.ExcelWriter(out,engine="openpyxl") as writer: data.to_excel(writer,index=False,sheet_name=report[:31])
    st.download_button("Download Excel",out.getvalue(),file_name=f"CEEKAY_Homes_{report}_{date.today()}.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

elif page == "Settings":
    header("Settings", "Connection and system setup")
    st.success(f"Connected to Google Sheet: {st.secrets.get('GOOGLE_SHEET_NAME','CEEKAY Homes Management')}")
    st.write("Service account:", st.secrets["gcp_service_account"].get("client_email",""))
    if st.button("Create / verify all worksheets"):
        try: svc.initialize(); st.success("All worksheets are ready")
        except Exception as e: st.error(str(e))
    st.warning("Never upload secrets.toml or a service-account JSON file to GitHub.")
