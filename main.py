import os
import sys
import asyncio
import time
import json
import copy
import base64
import flet as ft


def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


def main(page: ft.Page):
    page.title = "ORADO Kota Cirebon - The Law of Domino 101"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0F172A"
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    app_data_dir = os.environ.get("FLET_APP_STORAGE_DATA") or os.path.abspath(".")
    os.makedirs(app_data_dir, exist_ok=True)
    autosave_file = os.path.join(app_data_dir, "orado_autosave_2026.json")

    logo_path = resource_path("logo_orado_ok.png")
    logo_b64 = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode()

    state = {
        "nama_a": "TIM A",
        "nama_b": "TIM B",
        "skor_a": 0,
        "skor_b": 0,
        "set_a": 0,
        "set_b": 0,
        "set_ke": 1,
        "ronde_ke": 1,
        "format_match": 3,
        "getar_aktif": True,
        "selesai": False,
        "timer_detik": 30,
        "timer_jalan": False,
        "riwayat": [],
        "hasil_set": [],
    }

    undo_stack = []

    URUTAN_BALAK = [
        ("0-0", "Balak Kosong"),
        ("1-1", "Balak Satu"),
        ("2-2", "Balak Dua"),
        ("3-3", "Balak Tiga"),
        ("4-4", "Balak Empat"),
        ("5-5", "Balak Lima"),
        ("6-6", "Balak Enam"),
    ]

    def snapshot_state() -> dict:
        return {
            "nama_a": state["nama_a"],
            "nama_b": state["nama_b"],
            "skor_a": state["skor_a"],
            "skor_b": state["skor_b"],
            "set_a": state["set_a"],
            "set_b": state["set_b"],
            "set_ke": state["set_ke"],
            "ronde_ke": state["ronde_ke"],
            "format_match": state["format_match"],
            "getar_aktif": state["getar_aktif"],
            "selesai": state["selesai"],
            "timer_detik": state["timer_detik"],
            "riwayat": copy.deepcopy(state["riwayat"]),
            "hasil_set": copy.deepcopy(state["hasil_set"]),
        }

    def simpan_autosave():
        try:
            with open(autosave_file, "w", encoding="utf-8") as f:
                json.dump(snapshot_state(), f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def rekam_undo():
        undo_stack.append(snapshot_state())
        if len(undo_stack) > 40:
            undo_stack.pop(0)

    async def _animasi_getar_kontrol(target: ft.Control):
        if not state["getar_aktif"]:
            return
        try:
            for offset_x in (-7.0, 7.0, -5.0, 5.0, 0.0):
                target.offset = ft.Offset(offset_x * 0.015, 0.0)
                target.update()
                await asyncio.sleep(0.025)
        except Exception:
            pass

    def picu_getar(target: ft.Control):
        if not state["getar_aktif"]:
            return
        page.run_task(_animasi_getar_kontrol, target)

    def info_balak_sekarang():
        idx = (state["ronde_ke"] - 1) % 7
        return URUTAN_BALAK[idx]

    notif_text = ft.Text("", color="#F8FAFC", weight=ft.FontWeight.W_600)
    snack_bar = ft.SnackBar(content=notif_text, bgcolor="#1E293B", duration=2500)
    page.overlay.append(snack_bar)

    def tampilkan_notif(pesan: str, warna: str = "#1E293B"):
        notif_text.value = pesan
        snack_bar.bgcolor = warna
        snack_bar.open = True
        page.update()

    txt_set_info = ft.Text("SET 1 • BEST OF 3", size=13, weight=ft.FontWeight.BOLD, color="#38BDF8")
    txt_ronde_info = ft.Text("RONDE 1", size=13, weight=ft.FontWeight.BOLD, color="#FBBF24")
    txt_balak_kode = ft.Text("0-0", size=30, weight=ft.FontWeight.BOLD, color="#F8FAFC")
    txt_balak_nama = ft.Text("Pembuka: Balak Kosong", size=12, color="#94A3B8")

    txt_set_a = ft.Text("0", size=26, weight=ft.FontWeight.BOLD, color="#38BDF8")
    txt_set_b = ft.Text("0", size=26, weight=ft.FontWeight.BOLD, color="#F43F5E")

    input_nama_a = ft.TextField(
        value="TIM A",
        text_align=ft.TextAlign.CENTER,
        border_color="#334155",
        focused_border_color="#38BDF8",
        text_style=ft.TextStyle(size=17, weight=ft.FontWeight.BOLD, color="#F8FAFC"),
        on_change=lambda e: (state.update({"nama_a": e.control.value or "TIM A"}), simpan_autosave()),
    )
    input_nama_b = ft.TextField(
        value="TIM B",
        text_align=ft.TextAlign.CENTER,
        border_color="#334155",
        focused_border_color="#F43F5E",
        text_style=ft.TextStyle(size=17, weight=ft.FontWeight.BOLD, color="#F8FAFC"),
        on_change=lambda e: (state.update({"nama_b": e.control.value or "TIM B"}), simpan_autosave()),
    )

    txt_skor_a = ft.Text("0", size=68, weight=ft.FontWeight.BOLD, color="#38BDF8")
    txt_skor_b = ft.Text("0", size=68, weight=ft.FontWeight.BOLD, color="#F43F5E")

    input_poin_a = ft.TextField(
        label="Poin Ronde",
        keyboard_type=ft.KeyboardType.NUMBER,
        width=120,
        text_align=ft.TextAlign.CENTER,
        border_color="#334155",
    )
    input_poin_b = ft.TextField(
        label="Poin Ronde",
        keyboard_type=ft.KeyboardType.NUMBER,
        width=120,
        text_align=ft.TextAlign.CENTER,
        border_color="#334155",
    )

    txt_timer = ft.Text("30", size=30, weight=ft.FontWeight.BOLD, color="#22C55E")
    list_log = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, height=130)
    txt_rekap_set = ft.Text("Rekap Set: Belum ada set selesai", size=12, color="#94A3B8")

    mode_panggung = {"aktif": False}

    def tambah_log(teks: str):
        waktu = time.strftime("%H:%M:%S")
        state["riwayat"].insert(0, f"[{waktu}] {teks}")
        list_log.controls = [
            ft.Text(item, size=12, color="#CBD5E1") for item in state["riwayat"][:40]
        ]

    def perbarui_ringkasan_set():
        if not state["hasil_set"]:
            txt_rekap_set.value = "Rekap Set: Belum ada set selesai"
        else:
            ringkas = " | ".join(
                f"Set {item['set']}: {item['pemenang']} ({item['skor_a']}-{item['skor_b']}, {item['metode']})"
                for item in state["hasil_set"]
            )
            txt_rekap_set.value = f"Rekap Set: {ringkas}"

    def segarkan_tampilan():
        kode, nama = info_balak_sekarang()
        txt_set_info.value = f"SET {state['set_ke']} • BEST OF {state['format_match']}"
        txt_ronde_info.value = f"RONDE {state['ronde_ke']}"
        txt_balak_kode.value = kode
        txt_balak_nama.value = f"Pembuka: {nama}"
        txt_set_a.value = str(state["set_a"])
        txt_set_b.value = str(state["set_b"])
        txt_skor_a.value = str(state["skor_a"])
        txt_skor_b.value = str(state["skor_b"])
        list_log.controls = [
            ft.Text(item, size=12, color="#CBD5E1") for item in state["riwayat"][:40]
        ]
        perbarui_ringkasan_set()
        simpan_autosave()
        page.update()

    def catat_hasil_set(tim_menang: str, skor_a_akhir: int, skor_b_akhir: int, metode: str):
        nama_pemenang = state["nama_a"] if tim_menang == "A" else state["nama_b"]
        state["hasil_set"].append({
            "set": state["set_ke"],
            "pemenang": nama_pemenang,
            "skor_a": skor_a_akhir,
            "skor_b": skor_b_akhir,
            "metode": metode,
        })

    def cek_kemenangan_set():
        target_set = (state["format_match"] // 2) + 1
        if state["set_a"] >= target_set or state["set_b"] >= target_set:
            state["selesai"] = True
            state["timer_jalan"] = False
            pemenang = state["nama_a"] if state["set_a"] >= target_set else state["nama_b"]
            tambah_log(f"PERTANDINGAN SELESAI! Pemenang: {pemenang} ({state['set_a']}-{state['set_b']})")
            tampilkan_notif(f"PERTANDINGAN SELESAI! {pemenang} MENANG!", "#15803D")
        else:
            state["skor_a"] = 0
            state["skor_b"] = 0
            state["set_ke"] += 1
            state["ronde_ke"] = 1

    def proses_skor(tim: str, poin: int, keterangan: str = "Poin ronde", sumber_kontrol: ft.Control | None = None):
        picu_getar(sumber_kontrol or (kartu_a if tim == "A" else kartu_b))
        if state["selesai"]:
            tampilkan_notif("Pertandingan sudah selesai. Tekan 'Ulang Papan' untuk mulai baru.", "#B91C1C")
            return
        if poin <= 0:
            tampilkan_notif("Masukkan jumlah poin lebih dari 0.", "#B45309")
            return

        rekam_undo()

        if tim == "A":
            state["skor_a"] += poin
            nama_tim = state["nama_a"]
        else:
            state["skor_b"] += poin
            nama_tim = state["nama_b"]

        state["timer_detik"] = 30
        txt_timer.value = "30"
        txt_timer.color = "#22C55E"

        tambah_log(
            f"Set {state['set_ke']} R{state['ronde_ke']}: {nama_tim} +{poin} ({keterangan}) -> {state['skor_a']} - {state['skor_b']}"
        )

        if state["skor_a"] >= 101 or state["skor_b"] >= 101:
            tim_set = "A" if state["skor_a"] >= 101 else "B"
            if tim_set == "A":
                state["set_a"] += 1
            else:
                state["set_b"] += 1
            catat_hasil_set(tim_set, state["skor_a"], state["skor_b"], keterangan)
            tambah_log(f"SET {state['set_ke']} DIMENANGKAN {nama_tim} ({state['skor_a']}-{state['skor_b']})!")
            cek_kemenangan_set()
            segarkan_tampilan()
            return

        state["ronde_ke"] += 1
        segarkan_tampilan()

    def tombol_tambah_klik(tim: str, sumber_kontrol: ft.Control | None = None):
        field = input_poin_a if tim == "A" else input_poin_b
        try:
            nilai = int(field.value.strip())
        except (ValueError, AttributeError):
            picu_getar(sumber_kontrol or field)
            tampilkan_notif("Isi angka poin ronde terlebih dahulu.", "#B45309")
            return
        field.value = ""
        proses_skor(tim, nilai, "Poin ronde", sumber_kontrol=sumber_kontrol)

    def menang_spesial(tim: str, jenis: str, sumber_kontrol: ft.Control | None = None):
        picu_getar(sumber_kontrol or (kartu_a if tim == "A" else kartu_b))
        if state["selesai"]:
            return
        rekam_undo()
        nama_tim = state["nama_a"] if tim == "A" else state["nama_b"]
        if jenis == "APOLLO":
            if tim == "A":
                state["set_a"] += 2
            else:
                state["set_b"] += 2
            catat_hasil_set(tim, state["skor_a"], state["skor_b"], "APOLLO (+2 Set)")
            tambah_log(f"KEMENANGAN APOLLO! {nama_tim} langsung meraih +2 SET!")
            target_set = (state["format_match"] // 2) + 1
            if state["set_a"] >= target_set or state["set_b"] >= target_set:
                state["selesai"] = True
                state["timer_jalan"] = False
                tampilkan_notif(f"APOLLO! {nama_tim} MEMENANGKAN PERTANDINGAN!", "#15803D")
            else:
                state["skor_a"] = 0
                state["skor_b"] = 0
                state["set_ke"] += 1
                state["ronde_ke"] = 1
            segarkan_tampilan()
        elif jenis == "7BALAK":
            if tim == "A":
                state["set_a"] += 1
            else:
                state["set_b"] += 1
            catat_hasil_set(tim, state["skor_a"], state["skor_b"], "7 BALAK (+1 Set)")
            tambah_log(f"7 BALAK! {nama_tim} langsung memenangkan Set {state['set_ke']}!")
            cek_kemenangan_set()
            segarkan_tampilan()

    def batalkan_aksi_terakhir(e):
        picu_getar(e.control)
        if not undo_stack:
            tampilkan_notif("Tidak ada aksi yang dapat dibatalkan.", "#B45309")
            return
        prev = undo_stack.pop()
        state.update(prev)
        state["timer_jalan"] = False
        input_nama_a.value = state["nama_a"]
        input_nama_b.value = state["nama_b"]
        txt_timer.value = str(max(0, state["timer_detik"]))
        txt_timer.color = "#22C55E" if state["timer_detik"] > 10 else "#EF4444"
        btn_timer_toggle.content = "Mulai 30s"
        tambah_log("AKSI TERAKHIR DIBATALKAN (UNDO).")
        segarkan_tampilan()
        tampilkan_notif("Aksi terakhir berhasil dibatalkan.", "#0284C7")

    async def loop_timer():
        while state["timer_jalan"] and not state["selesai"]:
            await asyncio.sleep(1)
            if not state["timer_jalan"] or state["selesai"]:
                break
            state["timer_detik"] -= 1
            txt_timer.value = str(max(0, state["timer_detik"]))
            if state["timer_detik"] <= 10:
                txt_timer.color = "#EF4444"
            elif state["timer_detik"] <= 20:
                txt_timer.color = "#F59E0B"
            else:
                txt_timer.color = "#22C55E"
            page.update()

            if state["timer_detik"] <= 0:
                state["timer_jalan"] = False
                btn_timer_toggle.content = "Mulai 30s"
                picu_getar(panel_tengah_info)
                tambah_log("WAKTU 30 DETIK HABIS! Penalti +11 poin untuk lawan.")
                tampilkan_notif("Waktu 30 detik habis! Pilih tim penerima +11 poin penalti.", "#B91C1C")
                break

    def mulai_pause_timer(e):
        picu_getar(e.control)
        if state["selesai"]:
            return
        state["timer_jalan"] = not state["timer_jalan"]
        btn_timer_toggle.content = "Jeda Timer" if state["timer_jalan"] else "Mulai 30s"
        page.update()
        if state["timer_jalan"]:
            page.run_task(loop_timer)

    def reset_timer(e):
        picu_getar(e.control)
        state["timer_jalan"] = False
        state["timer_detik"] = 30
        txt_timer.value = "30"
        txt_timer.color = "#22C55E"
        btn_timer_toggle.content = "Mulai 30s"
        page.update()

    btn_timer_toggle = ft.Button(
        "Mulai 30s",
        icon=ft.Icons.TIMER,
        bgcolor="#2563EB",
        color="#FFFFFF",
        animate_offset=ft.Animation(110, ft.AnimationCurve.EASE_IN_OUT),
        on_click=mulai_pause_timer,
    )

    def eksekusi_reset_semua(e):
        picu_getar(e.control)
        dialog_reset.open = False
        undo_stack.clear()
        state.update({
            "skor_a": 0,
            "skor_b": 0,
            "set_a": 0,
            "set_b": 0,
            "set_ke": 1,
            "ronde_ke": 1,
            "selesai": False,
            "timer_detik": 30,
            "timer_jalan": False,
            "riwayat": [],
            "hasil_set": [],
        })
        txt_timer.value = "30"
        txt_timer.color = "#22C55E"
        btn_timer_toggle.content = "Mulai 30s"
        list_log.controls = []
        segarkan_tampilan()
        tampilkan_notif("Papan skor berhasil diulang ke awal.", "#0F766E")

    dialog_reset = ft.AlertDialog(
        modal=True,
        title=ft.Text("Ulang Pertandingan?"),
        content=ft.Text("Semua skor poin, skor set, rekap set, dan riwayat ronde saat ini akan dihapus dan kembali ke Set 1 Ronde 1."),
        actions=[
            ft.TextButton("Batal", on_click=lambda e: setattr(dialog_reset, "open", False) or page.update()),
            ft.Button("Ya, Ulang Papan", bgcolor="#DC2626", color="#FFFFFF", on_click=eksekusi_reset_semua),
        ],
    )
    page.overlay.append(dialog_reset)

    def buka_dialog_reset(e):
        picu_getar(e.control)
        dialog_reset.open = True
        page.update()

    async def salin_rekap_wa(e):
        picu_getar(e.control)
        status_txt = "SELESAI" if state["selesai"] else f"Berjalan - Set {state['set_ke']} Ronde {state['ronde_ke']}"
        if state["hasil_set"]:
            rincian_set = "\n".join(
                f"  Set {item['set']}: *{item['pemenang']}* ({item['skor_a']}-{item['skor_b']} • {item['metode']})"
                for item in state["hasil_set"]
            )
        else:
            rincian_set = "  (Belum ada set yang rampung)"

        kejadian_khusus = [
            line for line in reversed(state["riwayat"])
            if any(k in line for k in ("Penalti", "APOLLO", "7 BALAK", "WAKTU 30 DETIK HABIS"))
        ]
        log_khusus_txt = "\n".join(f"  - {item}" for item in kejadian_khusus[-10:]) if kejadian_khusus else "  (Tidak ada catatan penalti / kemenangan spesial)"

        teks_rekap = (
            f"*HASIL PERTANDINGAN DOMINO ORADO KOTA CIREBON (REGULASI 101)*\n"
            f"Format: Best of {state['format_match']}\n"
            f"----------------------------------\n"
            f"*{state['nama_a']}* : {state['set_a']} Set (Poin Set Berjalan: {state['skor_a']})\n"
            f"*{state['nama_b']}* : {state['set_b']} Set (Poin Set Berjalan: {state['skor_b']})\n"
            f"----------------------------------\n"
            f"*Rincian per Set:*\n{rincian_set}\n"
            f"----------------------------------\n"
            f"*Catatan Pelanggaran & Spesial:*\n{log_khusus_txt}\n"
            f"----------------------------------\n"
            f"Status: {status_txt}"
        )
        try:
            await ft.Clipboard().set(teks_rekap)
        except Exception:
            pass
        tampilkan_notif("Rekap lengkap per set & pelanggaran disalin (siap tempel ke WhatsApp)!", "#15803D")

    def ubah_format(e):
        rekam_undo()
        state["format_match"] = int(e.control.value)
        segarkan_tampilan()

    def ubah_getar(e):
        state["getar_aktif"] = e.control.value
        simpan_autosave()
        tampilkan_notif(
            "Paket Getar UI Aktif" if state["getar_aktif"] else "Paket Getar UI Dimatikan",
            "#1E293B",
        )

    dropdown_format = ft.Dropdown(
        label="Format Set",
        value="3",
        width=135,
        options=[
            ft.dropdown.Option("3", "Best of 3"),
            ft.dropdown.Option("5", "Best of 5"),
        ],
        on_select=ubah_format,
    )

    saklar_getar = ft.Switch(
        label="Getar UI",
        value=True,
        active_color="#38BDF8",
        on_change=ubah_getar,
    )

    logo_widget = (
        [ft.Image(src=logo_b64, width=48, height=48)]
        if logo_b64
        else []
    )

    header = ft.Column(
        [
            ft.Row(
                [
                    *logo_widget,
                    ft.Column(
                        [
                            ft.Text("ORADO KOTA CIREBON • DOMINO 101", size=17, weight=ft.FontWeight.BOLD, color="#F8FAFC"),
                            ft.Text("Federasi Olahraga Domino Nasional • 2026", size=11, color="#94A3B8"),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                ],
                spacing=10,
            ),
            ft.Row([dropdown_format, saklar_getar], spacing=10, wrap=True),
        ],
        spacing=10,
    )

    panel_tengah_info = ft.Container(
        bgcolor="#1E293B",
        border_radius=14,
        padding=14,
        border=ft.Border.all(1, "#334155"),
        animate_offset=ft.Animation(110, ft.AnimationCurve.EASE_IN_OUT),
        content=ft.Row(
            [
                ft.Column(
                    [
                        txt_set_info,
                        ft.Row(
                            [
                                ft.Text("SET:", size=13, color="#94A3B8"),
                                txt_set_a,
                                ft.Text("-", size=22, color="#64748B"),
                                txt_set_b,
                            ],
                            spacing=8,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Column(
                    [
                        txt_ronde_info,
                        txt_balak_kode,
                        txt_balak_nama,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=2,
                ),
                ft.Column(
                    [
                        ft.Text("SHOT CLOCK (30S)", size=11, weight=ft.FontWeight.BOLD, color="#94A3B8"),
                        txt_timer,
                        ft.Row(
                            [
                                btn_timer_toggle,
                                ft.OutlinedButton(
                                    "Reset",
                                    animate_offset=ft.Animation(110, ft.AnimationCurve.EASE_IN_OUT),
                                    on_click=reset_timer,
                                ),
                            ],
                            spacing=6,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
            wrap=True,
        ),
    )

    def buat_kartu_tim(tim: str, warna_aksen: str, input_nama: ft.TextField, txt_skor: ft.Text, input_poin: ft.TextField):
        btn_tambah = ft.Button(
            "+ Tambah Poin",
            bgcolor=warna_aksen,
            color="#FFFFFF",
            height=48,
            animate_offset=ft.Animation(110, ft.AnimationCurve.EASE_IN_OUT),
        )
        btn_tambah.on_click = lambda e, t=tim, b=btn_tambah: tombol_tambah_klik(t, b)

        btn_apollo = ft.Button(
            "APOLLO (+2 Set)",
            bgcolor="#7C3AED",
            color="#FFFFFF",
            animate_offset=ft.Animation(110, ft.AnimationCurve.EASE_IN_OUT),
        )
        btn_apollo.on_click = lambda e, t=tim, b=btn_apollo: menang_spesial(t, "APOLLO", b)

        btn_balak = ft.Button(
            "7 BALAK (+1 Set)",
            bgcolor="#0D9488",
            color="#FFFFFF",
            animate_offset=ft.Animation(110, ft.AnimationCurve.EASE_IN_OUT),
        )
        btn_balak.on_click = lambda e, t=tim, b=btn_balak: menang_spesial(t, "7BALAK", b)

        penalti_btns = []
        for nilai_pen in (11, 15, 20, 25):
            b_pen = ft.OutlinedButton(
                f"+{nilai_pen}",
                animate_offset=ft.Animation(110, ft.AnimationCurve.EASE_IN_OUT),
            )
            b_pen.on_click = lambda e, t=tim, p=nilai_pen, b=b_pen: proses_skor(t, p, f"Penalti +{p}", b)
            penalti_btns.append(b_pen)

        return ft.Container(
            bgcolor="#1E293B",
            border_radius=16,
            padding=16,
            border=ft.Border.all(2, warna_aksen),
            animate_offset=ft.Animation(110, ft.AnimationCurve.EASE_IN_OUT),
            content=ft.Column(
                [
                    input_nama,
                    txt_skor,
                    ft.Row(
                        [
                            input_poin,
                            btn_tambah,
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Divider(color="#334155"),
                    ft.Text("Sanksi Pelanggaran / Pass Palsu:", size=11, color="#94A3B8"),
                    ft.Row(
                        penalti_btns,
                        alignment=ft.MainAxisAlignment.CENTER,
                        wrap=True,
                        spacing=6,
                    ),
                    ft.Row(
                        [
                            btn_apollo,
                            btn_balak,
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        wrap=True,
                        spacing=8,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
        )

    kartu_a = buat_kartu_tim("A", "#0284C7", input_nama_a, txt_skor_a, input_poin_a)
    kartu_b = buat_kartu_tim("B", "#E11D48", input_nama_b, txt_skor_b, input_poin_b)

    panel_bawah = ft.Container(
        bgcolor="#1E293B",
        border_radius=14,
        padding=14,
        border=ft.Border.all(1, "#334155"),
        content=ft.Column(
            [
                ft.Text("RIWAYAT RONDE & PELANGGARAN", size=12, weight=ft.FontWeight.BOLD, color="#94A3B8"),
                ft.Row(
                    [
                        ft.Button(
                            "Undo Aksi",
                            icon=ft.Icons.UNDO,
                            bgcolor="#334155",
                            color="#FFFFFF",
                            animate_offset=ft.Animation(110, ft.AnimationCurve.EASE_IN_OUT),
                            on_click=batalkan_aksi_terakhir,
                        ),
                        ft.Button(
                            "Salin Rekap WA",
                            icon=ft.Icons.COPY,
                            bgcolor="#16A34A",
                            color="#FFFFFF",
                            animate_offset=ft.Animation(110, ft.AnimationCurve.EASE_IN_OUT),
                            on_click=salin_rekap_wa,
                        ),
                        ft.OutlinedButton(
                            "Ulang Papan",
                            icon=ft.Icons.REFRESH,
                            animate_offset=ft.Animation(110, ft.AnimationCurve.EASE_IN_OUT),
                            on_click=buka_dialog_reset,
                        ),
                    ],
                    spacing=8,
                    wrap=True,
                ),
                txt_rekap_set,
                list_log,
            ],
            spacing=10,
        ),
    )

    konten_utama = ft.Container(
        padding=14,
        visible=False,
        opacity=0.0,
        animate_opacity=ft.Animation(500, ft.AnimationCurve.EASE_OUT),
        content=ft.Column(
            [
                header,
                panel_tengah_info,
                kartu_a,
                kartu_b,
                panel_bawah,
            ],
            spacing=14,
        ),
    )

    def toggle_mode_panggung(e):
        picu_getar(e.control)
        mode_panggung["aktif"] = not mode_panggung["aktif"]
        panggung = mode_panggung["aktif"]
        btn_panggung.content = "Keluar Panggung" if panggung else "Mode Panggung"
        konten_utama.padding = 10 if panggung else 14
        txt_skor_a.size = 92 if panggung else 68
        txt_skor_b.size = 92 if panggung else 68
        txt_timer.size = 40 if panggung else 30
        txt_balak_kode.size = 40 if panggung else 30
        panel_bawah.visible = not panggung
        dropdown_format.visible = not panggung
        saklar_getar.visible = not panggung
        page.update()

    btn_panggung = ft.OutlinedButton(
        "Mode Panggung",
        icon=ft.Icons.TV,
        animate_offset=ft.Animation(110, ft.AnimationCurve.EASE_IN_OUT),
        on_click=toggle_mode_panggung,
    )
    header.controls[1].controls.append(btn_panggung)

    if os.path.exists(autosave_file):
        try:
            with open(autosave_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict) and (
                saved.get("skor_a", 0) > 0
                or saved.get("skor_b", 0) > 0
                or saved.get("set_a", 0) > 0
                or saved.get("set_b", 0) > 0
                or len(saved.get("riwayat", [])) > 0
            ):
                state.update(saved)
                input_nama_a.value = state["nama_a"]
                input_nama_b.value = state["nama_b"]
                dropdown_format.value = str(state.get("format_match", 3))
                saklar_getar.value = bool(state.get("getar_aktif", True))
                txt_timer.value = str(max(0, state.get("timer_detik", 30)))
        except Exception:
            pass

    splash_logo = ft.Container(
        width=190,
        height=190,
        border_radius=95,
        alignment=ft.Alignment(0, 0),
        bgcolor="#FFFFFF",
        border=ft.Border.all(4, "#F59E0B"),
        shadow=ft.BoxShadow(
            spread_radius=6,
            blur_radius=36,
            color="#DC2626",
        ),
        scale=0.35,
        opacity=0.0,
        animate_scale=ft.Animation(650, ft.AnimationCurve.EASE_OUT_BACK),
        animate_opacity=ft.Animation(500, ft.AnimationCurve.EASE_OUT),
        content=ft.Image(src=logo_b64, width=160, height=160) if logo_b64 else ft.Text("ORADO", size=30, weight=ft.FontWeight.BOLD, color="#DC2626"),
    )

    splash_title = ft.Column(
        [
            ft.Text(
                "ORADO KOTA CIREBON",
                size=24,
                weight=ft.FontWeight.BOLD,
                color="#F8FAFC",
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Text(
                "FEDERASI OLAHRAGA DOMINO NASIONAL",
                size=12,
                weight=ft.FontWeight.W_600,
                color="#FBBF24",
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Text(
                "THE LAW OF DOMINO 101 • 2026",
                size=11,
                color="#94A3B8",
                text_align=ft.TextAlign.CENTER,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=4,
        opacity=0.0,
        animate_opacity=ft.Animation(550, ft.AnimationCurve.EASE_IN),
    )

    splash_bar = ft.ProgressBar(
        width=220,
        color="#EF4444",
        bgcolor="#1E293B",
        value=0.0,
    )

    splash_screen = ft.Container(
        expand=True,
        height=680,
        bgcolor="#090D16",
        alignment=ft.Alignment(0, 0),
        opacity=1.0,
        animate_opacity=ft.Animation(450, ft.AnimationCurve.EASE_IN_OUT),
        content=ft.Column(
            [
                splash_logo,
                ft.Container(height=16),
                splash_title,
                ft.Container(height=20),
                splash_bar,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    async def jalankan_intro_ml():
        await asyncio.sleep(0.15)
        splash_logo.scale = 1.08
        splash_logo.opacity = 1.0
        splash_bar.value = 0.35
        page.update()

        await asyncio.sleep(0.55)
        splash_logo.scale = 1.0
        splash_title.opacity = 1.0
        splash_bar.value = 0.75
        page.update()

        await asyncio.sleep(0.70)
        splash_bar.value = 1.0
        page.update()

        await asyncio.sleep(0.40)
        splash_screen.opacity = 0.0
        page.update()

        await asyncio.sleep(0.40)
        splash_screen.visible = False
        konten_utama.visible = True
        page.update()

        await asyncio.sleep(0.05)
        konten_utama.opacity = 1.0
        segarkan_tampilan()

    page.add(splash_screen, konten_utama)
    page.run_task(jalankan_intro_ml)


ft.run(main)
