import os
import sys
import json
import subprocess
import time
import re
import shutil

# Ensure UTF-8 output and ANSI support in Windows terminal
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

if os.name == "nt":
    os.system("")

# ── TrueColor Modern Neon Theme ──────────────────────────────────────────────
CLR_MAIN    = "\033[38;2;168;85;247m"   # Neon Purple
CLR_CYAN    = "\033[38;2;6;182;212m"    # Electric Cyan
CLR_PINK    = "\033[38;2;236;72;153m"   # Neon Pink
CLR_GREEN   = "\033[38;2;16;185;129m"   # Emerald Green
CLR_YELLOW  = "\033[38;2;245;158;11m"   # Amber Gold
CLR_RED     = "\033[38;2;239;68;68m"    # Coral Red
CLR_WHITE   = "\033[38;2;249;250;251m"  # Crisp White
CLR_DIM     = "\033[38;2;156;163;175m"  # Slate Gray
CLR_BORDER  = "\033[38;2;75;85;99m"     # Sleek Dark Gray
CLR_BOLD    = "\033[1m"
R           = "\033[0m"

# Backward compatibility aliases
P = CLR_MAIN
C = CLR_CYAN
G = CLR_GREEN
Y = CLR_YELLOW
D = CLR_DIM
W = CLR_WHITE
RD = CLR_RED

WIDTH = 80
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def load_config():
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)


def banner(force_animate=False):
    from engine.banner import display_animated_banner
    display_animated_banner(force_animate=force_animate)


def visible_len(s: str) -> int:
    """Calculates visible terminal length by stripping ANSI escape sequences."""
    return len(re.sub(r'\033\[[0-9;]*m', '', s))


def box_header(title: str, width: int = WIDTH) -> str:
    inner = f"── [ {CLR_BOLD}{CLR_CYAN}{title}{R}{CLR_BORDER} ] "
    v = visible_len(inner)
    pad = max(0, width - 2 - v)
    return f"  {CLR_BORDER}╭{inner}" + "─" * pad + f"╮{R}"


def box_line(content: str, width: int = WIDTH) -> str:
    v = visible_len(content)
    pad = max(0, width - 2 - v)
    return f"  {CLR_BORDER}│{R}{content}" + " " * pad + f"{CLR_BORDER}│{R}"


def box_divider(title: str = "", width: int = WIDTH) -> str:
    if title:
        inner = f"── [ {CLR_BOLD}{CLR_CYAN}{title}{R}{CLR_BORDER} ] "
        v = visible_len(inner)
        pad = max(0, width - 2 - v)
        return f"  {CLR_BORDER}├{inner}" + "─" * pad + f"┤{R}"
    return f"  {CLR_BORDER}├" + "─" * (width - 2) + f"┤{R}"


def box_footer(width: int = WIDTH) -> str:
    return f"  {CLR_BORDER}╰" + "─" * (width - 2) + f"╯{R}"


def get_system_status():
    cfg = load_config()
    cap = cfg.get("nopecha") or cfg.get("solver") or {}
    mail_cfg = cfg.get("mail_services", {})
    vpn_cfg = cfg.get("vpn", {})

    active_mail = "None"
    for name in ["crowmail", "duckmail", "cybertemp", "tempmail_lol", "hotmail007", "lution", "zeus", "draxono", "mailcow"]:
        if mail_cfg.get(name, {}).get("enabled", False):
            active_mail = "CrowMail" if name == "crowmail" else ("DuckMail" if name == "duckmail" else name.capitalize())
            break

    threads = cfg.get("threading", {}).get("generator", cfg.get("threads", 1))
    vpn_on = vpn_cfg.get("enabled", False)
    vpn_str = f"{CLR_GREEN}Active (Auto-Rotate){R}" if vpn_on else f"{CLR_DIM}Direct / Off{R}"

    solver_key = cap.get("api_key", "").strip()
    mode = str(cap.get("solver_mode", "")).strip().lower()
    is_req = (mode in ("request", "req", "api")) or (cap.get("req_solver", False) and not cap.get("extension_solver", True))
    if not solver_key:
        solver_str = f"{CLR_RED}Key Missing{R}"
    elif is_req:
        solver_str = f"{CLR_GREEN}NopeCHA Request (API){R}"
    else:
        solver_str = f"{CLR_GREEN}NopeCHA Browser Ext{R}"

    verif = cfg.get("verification", {}).get("enabled", True)
    verif_str = f"{CLR_GREEN}Enabled{R}" if verif else f"{CLR_RED}Disabled{R}"

    return {
        "solver": solver_str,
        "mail": f"{CLR_CYAN}{active_mail}{R}",
        "vpn": vpn_str,
        "threads": f"{CLR_WHITE}{threads} Worker{R}" if int(threads) == 1 else f"{CLR_WHITE}{threads} Workers{R}",
        "verif": verif_str,
    }


def render_status_card(width: int = WIDTH):
    """Отрисовка карточки текущего состояния системы (решатель, почта, сеть, потоки)."""
    st = get_system_status()
    print(box_header("LIVE SYSTEM STATUS", width))
    col1_w = 38

    def make_row(label1, val1, label2, val2):
        s1 = f"   {CLR_DIM}{label1:<9}{R} {val1}"
        s1_pad = max(1, col1_w - visible_len(s1))
        s2 = f"{CLR_DIM}{label2:<11}{R} {val2}"
        return s1 + " " * s1_pad + s2

    print(box_line(make_row("Solver:", st["solver"], "Mail:", st["mail"]), width))
    print(box_line(make_row("Network:", st["vpn"], "Threads:", st["threads"]), width))
    print(box_line(make_row("Verif:", st["verif"], "Build:", f"{CLR_WHITE}v4.2 PRO{R}"), width))
    print(box_footer(width))


def main_menu():
    """Главное интерактивное меню терминала Lord Vault."""
    while True:
        clear()
        banner()
        print()
        render_status_card()
        print()

        # Секция 1: Основные инструменты
        print(box_header("MAIN SUITE"))
        print(box_line(f"   {CLR_GREEN}[01]{R}  {CLR_BOLD}{CLR_WHITE}EV Generator{R}          {CLR_DIM}· Multi-threaded Email-Verified account creator{R}"))
        print(box_line(f"   {CLR_YELLOW}[02]{R}  {CLR_BOLD}{CLR_WHITE}Token Checker{R}         {CLR_DIM}· Check token validity, nitro, flags & locks{R}"))
        print(box_line(f"   {CLR_PINK}[03]{R}  {CLR_BOLD}{CLR_WHITE}Token Joiner{R}          {CLR_DIM}· Invite link & OAuth2 guild joiner with bypass{R}"))
        print(box_line(f"   {CLR_YELLOW}[04]{R}  {CLR_BOLD}{CLR_WHITE}Setup Dependencies{R}    {CLR_DIM}· Install Python requirements & Node modules{R}"))
        print(box_line(f"   {CLR_RED}[05]{R}  {CLR_BOLD}{CLR_WHITE}Uninstall Modules{R}     {CLR_DIM}· Clean environment & purge cached packages{R}"))
        print(box_footer())
        print()

        # Секция 2: Конфигурация и диагностика
        print(box_header("CONFIG & DIAGNOSTICS"))
        print(box_line(f"   {CLR_MAIN}[06]{R}  {CLR_BOLD}{CLR_WHITE}Settings Hub{R}          {CLR_DIM}· Configure solver, mail services & threads{R}"))
        print(box_line(f"   {CLR_GREEN}[07]{R}  {CLR_BOLD}{CLR_WHITE}VPN & Network Status{R}  {CLR_DIM}· Inspect public IP & Mullvad/WARP clients{R}"))
        print(box_line(f"   {CLR_CYAN}[08]{R}  {CLR_BOLD}{CLR_WHITE}Proxy Checker Tool{R}    {CLR_DIM}· Test residential & datacenter proxy pools{R}"))
        print(box_line(f"   {CLR_DIM}[00]{R}  {CLR_BOLD}{CLR_WHITE}Exit Terminal{R}         {CLR_DIM}· Safely terminate all active sessions{R}"))
        print(box_footer())
        print()

        print(f"  {CLR_BORDER}╭─[{R} {CLR_BOLD}{CLR_MAIN}Lord Vault CLI{R} {CLR_BORDER}]──[{R} {CLR_DIM}Ready{R} {CLR_BORDER}]{R}")
        choice = input(f"  {CLR_BORDER}╰─➤{R} {CLR_BOLD}{CLR_CYAN}Select option{R} {CLR_DIM}›{R} ").strip()

        if choice in ("1", "01"):       start_generator()
        elif choice in ("2", "02"):     start_checker()
        elif choice in ("3", "03"):     start_joiner()
        elif choice in ("4", "04"):     setup()
        elif choice in ("5", "05"):     uninstall_setup()
        elif choice in ("6", "06"):     settings_menu()
        elif choice in ("7", "07"):     vpn_status()
        elif choice in ("8", "08"):     start_proxy_checker()
        elif choice in ("0", "00", "exit", "q"):
            print(f"\n  {CLR_GREEN}✓  Exiting Lord Vault. Goodbye!{R}\n")
            sys.exit(0)
        else:
            print(f"  {CLR_YELLOW}!  Invalid option. Please choose between 0 and 8.{R}")
            time.sleep(1)


def settings_menu():
    """Меню управления настройками приложения (потоки, капча, почта, авто-джойнер)."""
    while True:
        clear()
        banner()
        print()
        cfg = load_config()
        cap_cfg = cfg.get("nopecha") or cfg.get("solver", {})
        mail_cfg = cfg.get("mail_services", {})
        verif_cfg = cfg.get("verification", {})

        active_mail = "None"
        for name in ["crowmail", "duckmail", "cybertemp", "tempmail_lol", "hotmail007", "lution", "zeus", "draxono", "mailcow"]:
            if mail_cfg.get(name, {}).get("enabled", False):
                active_mail = "CrowMail" if name == "crowmail" else ("DuckMail" if name == "duckmail" else name.capitalize())
                break

        key_masked = cap_cfg.get("api_key", "")
        if key_masked:
            key_masked = key_masked[:4] + "***" + key_masked[-3:] if len(key_masked) > 7 else key_masked[:3] + "***"
        else:
            key_masked = "Not configured"

        threads_val = cfg.get("threading", {}).get("generator", cfg.get("threads", 1))
        verif_val = verif_cfg.get("enabled", True)
        solver_url = cap_cfg.get("url", "https://api.nopecha.com")

        print(box_header("CONFIGURATION & SETTINGS"))
        print(box_line(f"   {CLR_CYAN}[1]{R}  {CLR_BOLD}{CLR_WHITE}Worker Threads{R}          {CLR_DIM}· Currently:{R} {CLR_WHITE}{threads_val} Thread(s){R}"))
        print(box_line(f"   {CLR_CYAN}[2]{R}  {CLR_BOLD}{CLR_WHITE}Captcha API Key (NopeCHA){R} {CLR_DIM}· Currently:{R} {CLR_YELLOW}{key_masked}{R}"))
        print(box_line(f"   {CLR_CYAN}[3]{R}  {CLR_BOLD}{CLR_WHITE}Mail Provider Hub{R}        {CLR_DIM}· Currently:{R} {CLR_GREEN}{active_mail}{R}"))
        verif_text = "Enabled" if verif_val else "Disabled"
        print(box_line(f"   {CLR_CYAN}[4]{R}  {CLR_BOLD}{CLR_WHITE}Email Verification{R}       {CLR_DIM}· Currently:{R} {CLR_GREEN if verif_val else CLR_RED}{verif_text}{R}"))
        print(box_line(f"   {CLR_CYAN}[5]{R}  {CLR_BOLD}{CLR_WHITE}Solver Endpoint URL{R}      {CLR_DIM}· Currently:{R} {CLR_WHITE}{solver_url[:28]}...{R}"))
        print(box_line(f"   {CLR_CYAN}[6]{R}  {CLR_BOLD}{CLR_WHITE}Open config.json{R}         {CLR_DIM}· Open raw config in text editor{R}"))
        mode_val = str(cap_cfg.get("solver_mode", "")).strip().lower()
        is_req_val = (mode_val in ("request", "req", "api")) or (cap_cfg.get("req_solver", False) and not cap_cfg.get("extension_solver", True))
        mode_str = "Request (API)" if is_req_val else "Browser Extension"
        print(box_line(f"   {CLR_CYAN}[7]{R}  {CLR_BOLD}{CLR_WHITE}Solver Mode Toggle{R}      {CLR_DIM}· Currently:{R} {CLR_GREEN if is_req_val else CLR_CYAN}{mode_str}{R}"))
        aj_bot = cfg.get("auth_joiner", {}).get("bot", {})
        aj_ok = bool(aj_bot.get("id") and aj_bot.get("token"))
        aj_str = f"{CLR_GREEN}Configured{R}" if aj_ok else f"{CLR_YELLOW}Not Configured{R}"
        print(box_line(f"   {CLR_CYAN}[8]{R}  {CLR_BOLD}{CLR_WHITE}Auth Joiner (OAuth2){R}    {CLR_DIM}· Bot & Server:{R} {aj_str}"))
        print(box_line(f"   {CLR_DIM}[0]{R}  {CLR_BOLD}{CLR_WHITE}Back to Main Menu{R}"))
        print(box_footer())
        print()

        s = input(f"  {CLR_BORDER}╰─➤{R} {CLR_BOLD}{CLR_CYAN}Select setting{R} {CLR_DIM}›{R} ").strip()
        if s == "1":
            v = input(f"  {CLR_DIM}›› Enter thread count (e.g. 1, 2, 5): {R}").strip()
            try:
                val = max(1, int(v))
                cfg.setdefault("threading", {})["generator"] = val
                cfg["threads"] = val
                save_config(cfg)
                print(f"  {CLR_GREEN}✓  Worker threads set to {val}{R}")
            except ValueError:
                print(f"  {CLR_YELLOW}!  Invalid number{R}")
            time.sleep(1)
        elif s == "2":
            v = input(f"  {CLR_DIM}›› Enter NopeCHA API Key: {R}").strip()
            if "nopecha" not in cfg: cfg["nopecha"] = {}
            cfg["nopecha"]["api_key"] = v
            cfg["nopecha"]["enabled"] = True
            save_config(cfg)
            print(f"  {CLR_GREEN}✓  NopeCHA API key saved successfully{R}")
            time.sleep(1)
        elif s == "3":
            mail_services_menu(cfg)
        elif s == "4":
            if "verification" not in cfg: cfg["verification"] = {}
            cfg["verification"]["enabled"] = not cfg["verification"].get("enabled", True)
            save_config(cfg)
            state_str = "Enabled" if cfg["verification"]["enabled"] else "Disabled"
            print(f"  {CLR_GREEN}✓  Email Verification is now {state_str}{R}")
            time.sleep(1)
        elif s == "5":
            v = input(f"  {CLR_DIM}›› Enter Solver Endpoint URL: {R}").strip()
            if "nopecha" not in cfg: cfg["nopecha"] = {}
            if v:
                cfg["nopecha"]["url"] = v
                save_config(cfg)
                print(f"  {CLR_GREEN}✓  Solver URL updated to {v}{R}")
            time.sleep(1)
        elif s == "6":
            if os.name == "nt":
                os.system(f"notepad {CONFIG_FILE}")
            else:
                os.system(f"nano {CONFIG_FILE}")
        elif s == "7":
            clear()
            banner()
            print()
            print(box_header("SELECT CAPTCHA SOLVER MODE"))
            print(box_line(f"   {CLR_CYAN}[1]{R}  {CLR_BOLD}{CLR_WHITE}Browser Extension Solver (NopeCHA){R}"))
            print(box_line(f"        {CLR_DIM}· Solves hCaptcha directly inside real browser extension{R}"))
            print(box_line(f"   {CLR_CYAN}[2]{R}  {CLR_BOLD}{CLR_WHITE}Request-Based Solver (NopeCHA API / Token){R}"))
            print(box_line(f"        {CLR_DIM}· Solves hCaptcha via HTTP requests & API token polling{R}"))
            print(box_footer())
            sel = input(f"\n  {CLR_BORDER}╰─➤{R} {CLR_BOLD}{CLR_CYAN}Select mode (1 or 2, Enter to keep):{R} ").strip()
            if "nopecha" not in cfg: cfg["nopecha"] = {}
            if sel == "1":
                cfg["nopecha"]["solver_mode"] = "extension"
                cfg["nopecha"]["extension_solver"] = True
                cfg["nopecha"]["req_solver"] = False
                save_config(cfg)
                print(f"  {CLR_GREEN}✓ Solver mode changed to Browser Extension{R}")
            elif sel == "2":
                cfg["nopecha"]["solver_mode"] = "request"
                cfg["nopecha"]["extension_solver"] = False
                cfg["nopecha"]["req_solver"] = True
                save_config(cfg)
                print(f"  {CLR_GREEN}✓ Solver mode changed to Request-Based (NopeCHA API){R}")
            time.sleep(1)
        elif s == "8":
            auth_joiner_settings_menu(cfg)
        elif s == "0" or s == "":
            return


def auth_joiner_settings_menu(cfg):
    while True:
        clear()
        banner()
        print()
        aj = cfg.setdefault("auth_joiner", {})
        bot = aj.setdefault("bot", {})
        web = aj.setdefault("web", {})
        data = aj.setdefault("data", {})

        b_id = bot.get("id", "")
        b_sec = bot.get("secret", "")
        b_sec_masked = b_sec[:3] + "***" + b_sec[-3:] if len(b_sec) > 6 else ("Not set" if not b_sec else "***")
        b_tok = bot.get("token", "")
        b_tok_masked = b_tok[:6] + "***" + b_tok[-4:] if len(b_tok) > 10 else ("Not set" if not b_tok else "***")
        guild_id = data.get("guildId", "")
        redir = web.get("url", "http://localhost:3001")

        print(box_header("AUTH JOINER (OAUTH2) SETTINGS"))
        print(box_line(f"   {CLR_CYAN}[1]{R}  {CLR_BOLD}{CLR_WHITE}Bot Client ID{R}         {CLR_DIM}· Currently:{R} {CLR_WHITE}{b_id or 'Not set'}{R}"))
        print(box_line(f"   {CLR_CYAN}[2]{R}  {CLR_BOLD}{CLR_WHITE}Bot Client Secret{R}     {CLR_DIM}· Currently:{R} {CLR_YELLOW}{b_sec_masked}{R}"))
        print(box_line(f"   {CLR_CYAN}[3]{R}  {CLR_BOLD}{CLR_WHITE}Bot Token{R}             {CLR_DIM}· Currently:{R} {CLR_YELLOW}{b_tok_masked}{R}"))
        print(box_line(f"   {CLR_CYAN}[4]{R}  {CLR_BOLD}{CLR_WHITE}Target Guild (Server) ID{R} {CLR_DIM}· Currently:{R} {CLR_WHITE}{guild_id or 'Not set'}{R}"))
        print(box_line(f"   {CLR_CYAN}[5]{R}  {CLR_BOLD}{CLR_WHITE}OAuth2 Redirect URI{R}   {CLR_DIM}· Currently:{R} {CLR_WHITE}{redir}{R}"))
        print(box_line(f"   {CLR_CYAN}[6]{R}  {CLR_BOLD}{CLR_WHITE}Test Bot & Server Link{R} {CLR_DIM}· Verify permissions & invite URL{R}"))
        print(box_line(f"   {CLR_DIM}[0]{R}  {CLR_BOLD}{CLR_WHITE}Back to Settings Hub{R}"))
        print(box_footer())
        print()

        choice = input(f"  {CLR_BORDER}╰─➤{R} {CLR_BOLD}{CLR_CYAN}Select option{R} {CLR_DIM}›{R} ").strip()
        if choice == "1":
            v = input(f"  {CLR_DIM}›› Enter Bot Client ID: {R}").strip()
            if v:
                bot["id"] = v
                save_config(cfg)
                print(f"  {CLR_GREEN}✓  Bot Client ID saved{R}")
            time.sleep(1)
        elif choice == "2":
            v = input(f"  {CLR_DIM}›› Enter Bot Client Secret: {R}").strip()
            if v:
                bot["secret"] = v
                save_config(cfg)
                print(f"  {CLR_GREEN}✓  Bot Client Secret saved{R}")
            time.sleep(1)
        elif choice == "3":
            v = input(f"  {CLR_DIM}›› Enter Bot Token: {R}").strip()
            if v:
                bot["token"] = v
                save_config(cfg)
                print(f"  {CLR_GREEN}✓  Bot Token saved{R}")
            time.sleep(1)
        elif choice == "4":
            v = input(f"  {CLR_DIM}›› Enter Target Guild ID: {R}").strip()
            if v:
                data["guildId"] = v
                save_config(cfg)
                print(f"  {CLR_GREEN}✓  Target Guild ID saved{R}")
            time.sleep(1)
        elif choice == "5":
            v = input(f"  {CLR_DIM}›› Enter Redirect URI (default http://localhost:3001): {R}").strip()
            if v:
                web["url"] = v
                save_config(cfg)
                print(f"  {CLR_GREEN}✓  Redirect URI saved{R}")
            time.sleep(1)
        elif choice == "6":
            if not bot.get("token"):
                print(f"\n  {CLR_RED}[!] Please configure Bot Token first!{R}")
            else:
                from engine.auth_joiner import validate_bot_and_guild
                print()
                valid, msg = validate_bot_and_guild(bot.get("token", ""), data.get("guildId", ""), bot.get("id", ""))
                if valid:
                    print(f"\n  {CLR_GREEN}✓  Bot & Guild connection test PASSED!{R}")
                else:
                    print(f"\n  {CLR_RED}✗  Connection test: {msg}{R}")
            input(f"\n  {CLR_YELLOW}Press Enter to continue...{R}")
        elif choice in ("0", "back", "q"):
            break


def mail_services_menu(cfg):
    """Интерактивное меню выбора и настройки почтовых провайдеров."""
    PROVIDER_NAMES = {
        "crowmail": "CrowMail",
        "duckmail": "DuckMail",
        "cybertemp": "CyberTemp",
        "tempmail_lol": "TempMail.lol",
        "hotmail007": "Hotmail007",
        "lution": "Lution",
        "zeus": "Zeus",
        "draxono": "Draxono",
        "mailcow": "Mailcow",
    }
    PROVIDER_KEY_FIELD = {
        "crowmail": "password",
        "duckmail": "password",
        "cybertemp": "api_key",
        "tempmail_lol": None,
        "hotmail007": "client_key",
        "lution": "api_key",
        "zeus": "api_key",
        "draxono": "api_key",
        "mailcow": "api_key",
    }
    provider_order = ["crowmail", "duckmail", "cybertemp", "tempmail_lol", "hotmail007", "lution", "zeus", "draxono", "mailcow"]

    while True:
        clear()
        banner()
        print()
        if "mail_services" not in cfg:
            cfg["mail_services"] = {}
        ms = cfg["mail_services"]

        print(box_header("MAIL PROVIDER HUB"))
        for i, name in enumerate(provider_order, 1):
            svc = ms.get(name, {})
            enabled = svc.get("enabled", False)
            status = f"{CLR_GREEN}● ON {R}" if enabled else f"{CLR_DIM}○ OFF{R}"
            label = PROVIDER_NAMES.get(name, name)
            key_field = PROVIDER_KEY_FIELD.get(name)

            if key_field:
                val = svc.get(key_field, "")
                masked = (val[:3] + "***" if len(val) > 3 else val) if val else "Not set"
                info = f"{CLR_DIM}{key_field}: {masked}{R}"
            else:
                info = f"{CLR_DIM}No key required{R}"

            if name in ("lution", "zeus"):
                mcode = svc.get("mailcode", "")
                if mcode:
                    info += f" {CLR_DIM}| code: {mcode}{R}"

            line_str = f"   {CLR_CYAN}[{i}]{R}  {CLR_BOLD}{label:<13}{R} {status}  · {info}"
            print(box_line(line_str))

        print(box_divider("ACTIONS"))
        print(box_line(f"   {CLR_YELLOW}[K]{R}  {CLR_BOLD}{CLR_WHITE}Set Provider Key / Password{R}   {CLR_DIM}· Update API key or email password{R}"))
        print(box_line(f"   {CLR_YELLOW}[M]{R}  {CLR_BOLD}{CLR_WHITE}Set Mailcode / Domain{R}         {CLR_DIM}· Configure Lution/Zeus/Mailcow code{R}"))
        print(box_line(f"   {CLR_DIM}[0]{R}  {CLR_BOLD}{CLR_WHITE}Return to Settings{R}"))
        print(box_footer())
        print()

        s = input(f"  {CLR_BORDER}╰─➤{R} {CLR_BOLD}{CLR_CYAN}Toggle provider or select action{R} {CLR_DIM}›{R} ").strip()
        if s == "0" or s == "":
            return
        elif s.lower() in ("k", "key"):
            print(f"\n  {CLR_DIM}Available providers for key/password:{R}")
            for i, name in enumerate(provider_order, 1):
                kf = PROVIDER_KEY_FIELD.get(name)
                print(f"    {CLR_CYAN}[{i}]{R} {PROVIDER_NAMES[name]} {CLR_DIM}({kf or 'no key'}){R}")
            idx = input(f"\n  {CLR_DIM}›› Select provider [1-{len(provider_order)}]: {R}").strip()
            try:
                idx = int(idx) - 1
                if 0 <= idx < len(provider_order):
                    name = provider_order[idx]
                    key_field = PROVIDER_KEY_FIELD.get(name)
                    if key_field:
                        v = input(f"  {CLR_DIM}›› Enter {PROVIDER_NAMES[name]} {key_field}: {R}").strip()
                        if name not in ms: ms[name] = {"enabled": False}
                        ms[name][key_field] = v
                        cfg["mail_services"] = ms
                        save_config(cfg)
                        print(f"  {CLR_GREEN}✓  {PROVIDER_NAMES[name]} {key_field} updated successfully!{R}")
                    else:
                        print(f"  {CLR_DIM}  {PROVIDER_NAMES[name]} does not require credentials.{R}")
            except (ValueError, IndexError):
                print(f"  {CLR_YELLOW}!  Invalid selection{R}")
            time.sleep(1)
        elif s.lower() in ("m", "mailcode", "domain"):
            domain_providers = [p for p in provider_order if p in ("lution", "zeus", "mailcow")]
            print(f"\n  {CLR_DIM}Available providers for mailcode/domain:{R}")
            for i, name in enumerate(domain_providers, 1):
                print(f"    {CLR_CYAN}[{i}]{R} {PROVIDER_NAMES[name]}")
            idx = input(f"\n  {CLR_DIM}›› Select provider: {R}").strip()
            try:
                idx = int(idx) - 1
                if 0 <= idx < len(domain_providers):
                    name = domain_providers[idx]
                    if name not in ms: ms[name] = {"enabled": False}
                    if name == "lution":
                        mcode = input(f"  {CLR_DIM}›› Enter Lution Mailcode: {R}").strip().lower()
                        if mcode: ms[name]["mailcode"] = mcode
                    elif name == "zeus":
                        mcode = input(f"  {CLR_DIM}›› Enter Zeus Mailcode (e.g. HOTMAIL, OUTLOOK): {R}").strip()
                        if mcode: ms[name]["mailcode"] = mcode
                    elif name == "mailcow":
                        dom = input(f"  {CLR_DIM}›› Enter Mailcow Domain (e.g. yourdomain.com): {R}").strip()
                        if dom: ms[name]["domain"] = dom
                    cfg["mail_services"] = ms
                    save_config(cfg)
                    print(f"  {CLR_GREEN}✓  {PROVIDER_NAMES[name]} configuration updated!{R}")
            except (ValueError, IndexError):
                print(f"  {CLR_YELLOW}!  Invalid selection{R}")
            time.sleep(1)
        else:
            try:
                idx = int(s) - 1
                if 0 <= idx < len(provider_order):
                    target_name = provider_order[idx]
                    if target_name not in ms: ms[target_name] = {"enabled": False}

                    # Единственный активный провайдер: отключаем остальные, включаем выбранный
                    for n in provider_order:
                        if n in ms:
                            ms[n]["enabled"] = (n == target_name)
                        elif n == target_name:
                            ms[n] = {"enabled": True}

                    cfg["mail_services"] = ms
                    save_config(cfg)
                    print(f"  {CLR_GREEN}✓  {PROVIDER_NAMES[target_name]} is now the active mail provider!{R}")
                    time.sleep(1)
            except ValueError:
                pass


def vpn_status():
    """Проверка статуса подключений VPN (Mullvad, WARP), ротации и публичного IP."""
    clear()
    banner()
    print()
    import requests

    cfg = load_config()
    vpn_cfg = cfg.get("vpn", {})
    vpn_enabled = vpn_cfg.get("enabled", False)
    reconnect_cmd = vpn_cfg.get("reconnect_command", "")
    rotate_country = vpn_cfg.get("rotate_country", True)

    print(box_header("VPN & NETWORK STATUS"))
    vpn_act = "Active (ON)" if vpn_enabled else "Disabled (OFF)"
    print(box_line(f"   {CLR_DIM}VPN Rotation:{R}    {CLR_GREEN if vpn_enabled else CLR_RED}{vpn_act}{R}"))
    rc_act = "Enabled" if rotate_country else "Disabled"
    print(box_line(f"   {CLR_DIM}Rotate Country:{R}  {CLR_GREEN if rotate_country else CLR_RED}{rc_act}{R}"))
    if reconnect_cmd:
        print(box_line(f"   {CLR_DIM}Reconnect Cmd:{R}   {CLR_WHITE}{reconnect_cmd[:55]}...{R}"))

    # Поиск установленных клиентов VPN в системе
    mullvad_cli = r"C:\Program Files\Mullvad VPN\resources\mullvad.exe"
    if not os.path.exists(mullvad_cli): mullvad_cli = "mullvad"

    VPN_CHECKS = {
        "mullvad": ([mullvad_cli, "status"], "Mullvad VPN"),
        "warp": ([r"C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe", "--version"], "Cloudflare WARP"),
        "nordvpn": (["nordvpn", "--version"], "NordVPN"),
        "windscribe": (["windscribe", "status"], "Windscribe"),
        "expressvpn": (["expressvpn", "status"], "ExpressVPN"),
        "protonvpn": (["protonvpn-cli", "status"], "ProtonVPN"),
        "surfshark": (["surfshark-vpn", "status"], "Surfshark"),
    }
    detected = []
    for key, (cmd, name) in VPN_CHECKS.items():
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
            detected.append((name, result.stdout.strip()[:40]))
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    print(box_divider("DETECTED VPN CLIENTS"))
    if detected:
        for name, info in detected:
            print(box_line(f"   {CLR_GREEN}✓{R} {CLR_BOLD}{name:<16}{R} {CLR_DIM}· {info}{R}"))
    else:
        print(box_line(f"   {CLR_YELLOW}○ No standard VPN CLI detected in PATH{R}"))
        print(box_line(f"   {CLR_DIM}  Supported: Mullvad VPN, Cloudflare WARP, NordVPN, Windscribe{R}"))

    # Определение внешнего IP адреса
    print(box_divider("PUBLIC IP INSPECTION"))
    try:
        ip = requests.get("https://api.ipify.org", timeout=5).text.strip()
        print(box_line(f"   {CLR_CYAN}Current Public IP:{R} {CLR_BOLD}{CLR_GREEN}{ip}{R}"))
    except Exception:
        print(box_line(f"   {CLR_RED}Could not reach IP inspection service{R}"))

    print(box_footer())
    print()

    toggle = input(f"  {CLR_BORDER}╰─➤{R} {CLR_CYAN}Toggle VPN?{R} {CLR_DIM}(on / off / Enter to skip):{R} ").strip().lower()
    if toggle == "on":
        cfg.setdefault("vpn", {})["enabled"] = True
        save_config(cfg)
        print(f"  {CLR_GREEN}✓  VPN rotation enabled!{R}")
        time.sleep(1)
    elif toggle == "off":
        cfg.setdefault("vpn", {})["enabled"] = False
        save_config(cfg)
        print(f"  {CLR_YELLOW}✓  VPN rotation disabled.{R}")
        time.sleep(1)


def start_generator():
    """Запуск основного генератора аккаунтов (main.py)."""
    clear()
    banner()
    print()
    print(box_header("LAUNCHING TOKEN GENERATOR"))
    print(box_line(f"   {CLR_GREEN}✓ Starting multi-threaded Discord creator...{R}"))
    print(box_line(f"   {CLR_DIM}· Press CTRL+C at any time to halt generation safely.{R}"))
    print(box_footer())
    print()
    subprocess.run([sys.executable, "main.py"], cwd=BASE_DIR)
    print(f"\n  {CLR_YELLOW}›› Generator stopped. Press Enter to return...{R}")
    input()


def start_joiner():
    """Запуск модуля скоростного джойнера токенов (engine/joiner.py)."""
    clear()
    banner()
    print()
    joiner_script = os.path.join(BASE_DIR, "engine", "joiner.py")
    if not os.path.exists(joiner_script):
        print(f"  {CLR_RED}[!] Joiner engine not found at {joiner_script}{R}")
        input(f"  {CLR_YELLOW}Press Enter to return...{R}")
        return
    subprocess.run([sys.executable, "engine/joiner.py"], cwd=BASE_DIR)


def start_auth_joiner():
    start_joiner()


def start_link_joiner():
    start_joiner()


def start_checker():
    """Запуск чекера токенов (engine/checker.py)."""
    clear()
    banner()
    print()
    print(box_header("STARTING TOKEN CHECKER"))
    print(box_footer())
    print()
    subprocess.run([sys.executable, "engine/checker.py"], cwd=BASE_DIR)
    print(f"\n  {CLR_YELLOW}›› Token Checker finished. Press Enter to return...{R}")
    input()


def start_proxy_checker():
    """Запуск чекера прокси (engine/proxy_checker.py)."""
    clear()
    banner()
    print()
    print(box_header("STARTING PROXY CHECKER TOOL"))
    print(box_footer())
    print()
    subprocess.run([sys.executable, os.path.join("engine", "proxy_checker.py")], cwd=BASE_DIR)
    print(f"\n  {CLR_YELLOW}›› Proxy Checker finished. Press Enter to return...{R}")
    input()


def setup():
    """Автоматическая установка и обновление зависимостей Python и Node.js."""
    clear()
    banner()
    print()
    print(box_header("INSTALLING DEPENDENCIES & ENVIRONMENT"))
    print(box_line(f"   {CLR_CYAN}› Installing Python pip dependencies...{R}"))
    print(box_footer())
    print()
    req_path = os.path.join(BASE_DIR, "requirements.txt")
    os.system(f"pip install -r \"{req_path}\"")

    auth_dir = os.path.join(BASE_DIR, "engine", "auth_joiner")
    if os.path.exists(auth_dir):
        if shutil.which("npm"):
            print(f"\n  {CLR_CYAN}› Installing Auth Joiner Node modules...{R}\n")
            subprocess.run(["npm", "i"], cwd=auth_dir, shell=True)
        else:
            print(f"  {CLR_DIM}› Node.js/npm not found; using pure Python Auth Joiner.{R}")

    print(f"\n  {CLR_GREEN}✓  Setup complete! All packages installed successfully.{R}\n")
    input(f"  {CLR_YELLOW}Press Enter to return...{R}")


def uninstall_setup():
    """Полное удаление установленных пакетов и очистка рабочей директории."""
    clear()
    banner()
    print()
    print(box_header("UNINSTALLING SETUP & CLEANING ENVIRONMENT"))
    print(box_line(f"   {CLR_RED}› Removing Python packages and node_modules...{R}"))
    print(box_footer())
    print()
    req_path = os.path.join(BASE_DIR, "requirements.txt")
    os.system(f"pip uninstall -y -r \"{req_path}\"")

    auth_dir = os.path.join(BASE_DIR, "engine", "auth_joiner")
    node_modules_dir = os.path.join(auth_dir, "node_modules")
    if os.path.exists(node_modules_dir):
        print(f"\n  {CLR_DIM}› Removing node_modules...{R}")
        if os.name == "nt":
            os.system(f"rmdir /s /q \"{node_modules_dir}\"")
        else:
            os.system(f"rm -rf \"{node_modules_dir}\"")

        pkg_lock = os.path.join(auth_dir, "package-lock.json")
        if os.path.exists(pkg_lock):
            os.remove(pkg_lock)

    print(f"\n  {CLR_GREEN}✓  Clean uninstall complete!{R}\n")
    input(f"  {CLR_YELLOW}Press Enter to return...{R}")


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n  {CLR_YELLOW}›› Exiting Lord Vault...{R}")
        sys.exit(0)

