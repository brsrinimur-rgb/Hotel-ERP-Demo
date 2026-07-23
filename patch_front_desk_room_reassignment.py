from pathlib import Path
import shutil
import sys

TARGET = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('app.py')

OLD = '''    with t1:
        if reserved_df.empty:
            st.info("No pending reservations are available for check-in.")
        else:
            labels={r["reservation_id"]:f'{r["reservation_id"]} | {r["guest_name"]} | Room {r["room_no"]} | {r["checkin_date"]}' for _,r in reserved_df.iterrows()}
            rid=st.selectbox("Select Arrival",reserved_df["reservation_id"].tolist(),format_func=lambda x:labels.get(x,x))
            row=reserved_df[reserved_df["reservation_id"]==rid].iloc[0]
            c1,c2,c3,c4=st.columns(4)
            c1.metric("Guest",str(row["guest_name"]))
            c2.metric("Room",str(row["room_no"]))
            c3.metric("Arrival",str(row["checkin_date"]))
            c4.metric("Deposit",money(row["deposit"]))
            verify=st.checkbox("Guest identity and reservation details verified")
            if st.button("Check-in Guest",type="primary",disabled=not verify,use_container_width=True):
                room=str(row["room_no"])
                hk=scalar("SELECT housekeeping FROM rooms WHERE room_no=?",(room,),"Unknown")
                if str(hk).lower() not in {"clean","ready"}:
                    st.error(f"Room {room} is not ready. Housekeeping status: {hk}")
                else:
                    execute("UPDATE reservations SET status='Checked-in' WHERE reservation_id=?",(rid,))
                    execute("UPDATE rooms SET status='Occupied' WHERE room_no=?",(room,))
                    st.success(f"{row['guest_name']} checked in to room {room}.")
                    st.rerun()
'''

NEW = '''    with t1:
        if reserved_df.empty:
            st.info("No pending reservations are available for check-in.")
        else:
            labels = {
                r["reservation_id"]:
                f'{r["reservation_id"]} | {r["guest_name"]} | Room {r["room_no"]} | {r["checkin_date"]}'
                for _, r in reserved_df.iterrows()
            }
            rid = st.selectbox(
                "Select Arrival",
                reserved_df["reservation_id"].tolist(),
                format_func=lambda x: labels.get(x, x),
            )
            row = reserved_df[reserved_df["reservation_id"] == rid].iloc[0]
            current_room = str(row["room_no"])

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Guest", str(row["guest_name"]))
            c2.metric("Room", current_room)
            c3.metric("Arrival", str(row["checkin_date"]))
            c4.metric("Deposit", money(row["deposit"]))

            hk = scalar(
                "SELECT housekeeping FROM rooms WHERE room_no=?",
                (current_room,),
                "Unknown",
            )
            room_ready = str(hk).strip().lower() in {"clean", "ready"}

            if room_ready:
                st.success(f"Room {current_room} is ready for check-in.")
            else:
                st.error(
                    f"Room {current_room} is not ready. "
                    f"Housekeeping status: {hk}"
                )

                ready_rooms = query("""
                    SELECT room_no, room_type, rate, housekeeping
                    FROM rooms
                    WHERE status='Available'
                      AND LOWER(COALESCE(housekeeping,'')) IN ('clean','ready')
                      AND CAST(room_no AS TEXT) <> ?
                    ORDER BY room_type, room_no
                """, (current_room,))

                if ready_rooms.empty:
                    st.warning("No clean and available replacement rooms are currently available.")
                else:
                    st.markdown("#### Assign another room before check-in")
                    room_options = ready_rooms["room_no"].astype(str).tolist()
                    room_labels = {
                        str(r["room_no"]):
                        f'Room {r["room_no"]} | {r["room_type"]} | {money(r["rate"])} | {r["housekeeping"]}'
                        for _, r in ready_rooms.iterrows()
                    }
                    new_room = st.selectbox(
                        "Select replacement room",
                        room_options,
                        key=f"precheckin_room_{rid}",
                        format_func=lambda x: room_labels.get(str(x), str(x)),
                    )
                    reason = st.text_input(
                        "Reason for reassignment",
                        value=f"Original room {current_room} not ready ({hk})",
                        key=f"precheckin_reason_{rid}",
                    )
                    if st.button(
                        "Assign New Room",
                        type="primary",
                        use_container_width=True,
                        key=f"assign_new_room_{rid}",
                    ):
                        room_check = query("""
                            SELECT room_no
                            FROM rooms
                            WHERE CAST(room_no AS TEXT)=?
                              AND status='Available'
                              AND LOWER(COALESCE(housekeeping,'')) IN ('clean','ready')
                        """, (str(new_room),))

                        if room_check.empty:
                            st.error("The selected room is no longer available. Please select another room.")
                        else:
                            execute(
                                "UPDATE reservations SET room_no=? WHERE reservation_id=? AND status='Reserved'",
                                (str(new_room), rid),
                            )
                            execute(
                                "UPDATE rooms SET status='Available' WHERE room_no=?",
                                (current_room,),
                            )
                            execute(
                                "UPDATE rooms SET status='Reserved' WHERE room_no=?",
                                (str(new_room),),
                            )
                            try:
                                execute("""
                                    INSERT INTO audit_log
                                    (action, reference, details, created_at)
                                    VALUES (?, ?, ?, ?)
                                """, (
                                    "Pre-check-in room reassignment",
                                    rid,
                                    f"Room {current_room} changed to {new_room}. Reason: {reason}",
                                    datetime.now().isoformat(timespec="seconds"),
                                ))
                            except Exception:
                                pass

                            st.success(
                                f"Reservation {rid} reassigned from room "
                                f"{current_room} to room {new_room}."
                            )
                            st.rerun()

            verify = st.checkbox(
                "Guest identity and reservation details verified",
                key=f"verify_checkin_{rid}",
            )

            if st.button(
                "Check-in Guest",
                type="primary",
                disabled=(not verify or not room_ready),
                use_container_width=True,
                key=f"checkin_guest_{rid}",
            ):
                room_state = query("""
                    SELECT status, housekeeping
                    FROM rooms
                    WHERE room_no=?
                """, (current_room,))

                if room_state.empty:
                    st.error(f"Room {current_room} was not found.")
                else:
                    status = str(room_state.iloc[0]["status"])
                    hk_now = str(room_state.iloc[0]["housekeeping"])
                    if status not in {"Reserved", "Available"}:
                        st.error(
                            f"Room {current_room} cannot be checked in. "
                            f"Current room status: {status}"
                        )
                    elif hk_now.strip().lower() not in {"clean", "ready"}:
                        st.error(
                            f"Room {current_room} is not ready. "
                            f"Housekeeping status: {hk_now}"
                        )
                    else:
                        execute(
                            "UPDATE reservations SET status='Checked-in' WHERE reservation_id=? AND status='Reserved'",
                            (rid,),
                        )
                        execute(
                            "UPDATE rooms SET status='Occupied' WHERE room_no=?",
                            (current_room,),
                        )
                        st.success(
                            f"{row['guest_name']} checked in to room {current_room}."
                        )
                        st.rerun()
'''

if not TARGET.exists():
    raise SystemExit(f'File not found: {TARGET.resolve()}')

source = TARGET.read_text(encoding='utf-8')
if OLD not in source:
    raise SystemExit(
        'The expected Front Desk block was not found. '
        'Use this patch on the latest app.py file.'
    )

backup = TARGET.with_suffix(TARGET.suffix + '.backup_before_room_fix')
shutil.copy2(TARGET, backup)
TARGET.write_text(source.replace(OLD, NEW, 1), encoding='utf-8')

print(f'Updated: {TARGET.resolve()}')
print(f'Backup:  {backup.resolve()}')
print('Front Desk pre-check-in room reassignment added successfully.')
