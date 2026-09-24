#define UNICODE
#define _UNICODE
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <windowsx.h>
#include <commctrl.h>
#include <commdlg.h>
#include <shellapi.h>

#include "model.h"

#include <algorithm>
#include <filesystem>
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#pragma comment(lib, "Comctl32.lib")

namespace {
using namespace gidmg;

constexpr wchar_t kAppClass[] = L"GiDMG.NativeWindow";
constexpr wchar_t kVersion[] = L"2.2.0";
constexpr int kLeftWidth = 252;
constexpr int kRightWidth = 328;

enum : int {
    IDC_CONFIG_LIST = 100,
    IDC_CONFIG_NAME = 101,
    IDC_CONFIG_NEW = 102,
    IDC_CONFIG_OPEN = 103,
    IDC_CONFIG_DELETE = 104,
    IDC_CONFIG_REFRESH = 105,
    IDC_CONFIG_FORMULA = 106,
    IDC_NAV_MONSTER = 200,
    IDC_NAV_CHARACTERS = 201,
    IDC_NAV_TIMELINE = 202,
    IDC_NAV_HISTORY = 203,
    IDC_ADD_CHARACTER = 204,
    IDC_ISLAND_SAVE = 210,
    IDC_ISLAND_DISCARD = 211,
    IDC_ISLAND_QUICK = 212,
    IDC_ISLAND_SETTINGS = 213,
    IDC_TOOL_IMPORT = 220,
    IDC_TOOL_EXPORT = 221,
    IDC_TOOL_MORE = 222,
    IDC_TOOL_FORMULA = 223,
    IDC_TOOL_DETAILS = 224,
    IDC_TOOL_SHARE = 225,
    IDC_ADD_SOURCE = 230,
    IDC_ADD_BASELINE = 231,
    IDC_MONSTER_LEVEL = 240,
    IDC_ROTATION = 241,
    IDC_TIMELINE_TOGGLE = 242,
    IDC_DAMAGE_SHARE_TOGGLE = 243,
    IDC_SAVE_SETTINGS = 244,
    IDC_CHAR_BASE = 1000,
    IDC_CHAR_NAME = 1200,
    IDC_CHAR_ELEMENT = 1201,
    IDC_CHAR_LEVEL = 1202,
    IDC_CHAR_BASE_ATK = 1203,
    IDC_CHAR_BASE_HP = 1204,
    IDC_CHAR_WEAPON_ATK = 1205,
    IDC_CHAR_ATK_PCT = 1206,
    IDC_CHAR_EM = 1207,
    IDC_CHAR_CRIT = 1208,
    IDC_CHAR_CD = 1209,
    IDC_CHAR_DELETE = 1210,
    IDC_SOURCE_BASE = 1400,
    IDC_RES_BASE = 1600
};

enum class Workspace { Character, Monster, Timeline, History };
enum class Screen { Manager, Main };

struct ControlInfo { HWND handle = nullptr; int id = 0; };

COLORREF Mix(COLORREF a, COLORREF b, double amount) {
    auto ch = [amount](int x, int y) { return static_cast<BYTE>(x + (y - x) * amount); };
    return RGB(ch(GetRValue(a), GetRValue(b)), ch(GetGValue(a), GetGValue(b)), ch(GetBValue(a), GetBValue(b)));
}
std::wstring Number(double value, int decimals = 0) {
    wchar_t buffer[80];
    if (decimals == 0) swprintf_s(buffer, L"%.0f", value); else swprintf_s(buffer, L"%.1f", value);
    return buffer;
}
std::wstring Total(double value) {
    if (value >= 100000000) return Number(value / 100000000.0, 2) + L" 亿";
    if (value >= 10000) return Number(value / 10000.0, 2) + L" 万";
    return Number(value);
}
std::wstring ElementName(const std::string& element) {
    static const std::map<std::string, std::wstring> names{{"pyro",L"火"},{"hydro",L"水"},{"electro",L"雷"},{"cryo",L"冰"},{"dendro",L"草"},{"anemo",L"风"},{"geo",L"岩"},{"physical",L"物理"}};
    auto it = names.find(element); return it == names.end() ? L"元素" : it->second;
}
COLORREF ElementColor(const std::string& element) {
    if (element == "pyro") return RGB(215, 90, 58); if (element == "hydro") return RGB(42,127,190); if (element == "electro") return RGB(125,85,199); if (element == "cryo") return RGB(58,157,184); if (element == "dendro") return RGB(90,154,58); if (element == "anemo") return RGB(43,155,127); if (element == "geo") return RGB(184,138,45); return RGB(106,95,87);
}

class NativeApp {
public:
    explicit NativeApp(HINSTANCE instance) : instance_(instance), store_(ExecutableDirectory()) {}
    int Run();
    static LRESULT CALLBACK WindowProc(HWND, UINT, WPARAM, LPARAM);
private:
    std::filesystem::path ExecutableDirectory() const {
        wchar_t path[MAX_PATH]{}; GetModuleFileNameW(instance_, path, MAX_PATH); return std::filesystem::path(path).parent_path();
    }
    void CreateMainWindow();
    void ClearControls();
    HWND Button(int id, const std::wstring& text, int x, int y, int width, int height, DWORD extra = 0);
    HWND Edit(int id, const std::wstring& text, int x, int y, int width, int height, bool numeric = false);
    HWND Combo(int id, const std::vector<std::wstring>& values, int selected, int x, int y, int width, int height);
    HWND Label(const std::wstring& text, int x, int y, int width, int height, DWORD style = 0);
    void SetFont(HWND handle, bool bold = false, int size = 9);
    void BuildManager();
    void BuildMain();
    void BuildCharacterControls(int left, int top, int width);
    void BuildMonsterControls(int left, int top, int width);
    void BuildTimelineControls(int left, int top, int width);
    void BuildHistoryControls(int left, int top, int width);
    void LayoutMain();
    void Paint(HDC dc);
    void PaintManager(HDC dc, const RECT& client);
    void PaintMain(HDC dc, const RECT& client);
    void DrawTextLine(HDC dc, const std::wstring& text, RECT rect, COLORREF color, int size = 9, bool bold = false, UINT format = DT_LEFT | DT_VCENTER | DT_SINGLELINE);
    void Fill(HDC dc, RECT rect, COLORREF color);
    void Round(HDC dc, RECT rect, COLORREF fill, COLORREF border, int radius = 12);
    void OnCommand(WPARAM wParam, LPARAM lParam);
    void OnMouseMove(int x, int y);
    void OpenSelectedConfig();
    void NewConfig();
    void SaveConfig(bool leave);
    void LeaveWithoutSaving();
    void Recalculate(bool repaint = true);
    void UpdateSelectedFromControls();
    void SelectCharacter(size_t index);
    void AddCharacter();
    void AddSource();
    void ShowSettings();
    void ShowFormula();
    void ShowQuickTable();
    void ShowDetails();
    void ShowShare();
    void ImportConfig();
    void ExportConfig();
    void ResetConfig();
    void AppendHistory();
    void LoadManagerList();
    void SetWorkspace(Workspace workspace);
    bool IsMain() const { return screen_ == Screen::Main; }
    Character* CurrentCharacter();
    const Character* CurrentCharacter() const;
    double EditNumber(int id, double fallback = 0) const;
    std::wstring EditText(int id) const;
    void SetText(int id, const std::wstring& text);
    HWND Find(int id) const;

    HINSTANCE instance_ = nullptr;
    HWND window_ = nullptr;
    HFONT regularFont_ = nullptr;
    HFONT smallFont_ = nullptr;
    HFONT boldFont_ = nullptr;
    HFONT titleFont_ = nullptr;
    Screen screen_ = Screen::Manager;
    Workspace workspace_ = Workspace::Character;
    ConfigStore store_;
    Config config_;
    Config savedConfig_;
    std::filesystem::path currentPath_;
    Calculation calculation_;
    size_t selectedCharacter_ = 0;
    bool islandExpanded_ = true;
    bool moreMenu_ = false;
    POINT lastMouse_{};
    std::vector<HWND> controls_;
    std::map<int, HWND> byId_;
};

NativeApp* g_app = nullptr;

int NativeApp::Run() {
    INITCOMMONCONTROLSEX common{sizeof(common), ICC_STANDARD_CLASSES | ICC_LISTVIEW_CLASSES}; InitCommonControlsEx(&common);
    CreateMainWindow();
    ShowWindow(window_, SW_SHOW); UpdateWindow(window_); BuildManager();
    MSG message{}; while (GetMessageW(&message, nullptr, 0, 0) > 0) { TranslateMessage(&message); DispatchMessageW(&message); }
    if (regularFont_) DeleteObject(regularFont_); if (smallFont_) DeleteObject(smallFont_); if (boldFont_) DeleteObject(boldFont_); if (titleFont_) DeleteObject(titleFont_); return static_cast<int>(message.wParam);
}

void NativeApp::CreateMainWindow() {
    WNDCLASSEXW wc{sizeof(wc)}; wc.hInstance = instance_; wc.lpfnWndProc = WindowProc; wc.lpszClassName = kAppClass; wc.hCursor = LoadCursorW(nullptr, IDC_ARROW); wc.hbrBackground = CreateSolidBrush(RGB(243,245,248)); wc.style = CS_HREDRAW | CS_VREDRAW; RegisterClassExW(&wc);
    window_ = CreateWindowExW(0, kAppClass, L"Gi DMG v2.2.0 · 原神伤害计算器", WS_OVERLAPPEDWINDOW | WS_CLIPCHILDREN, CW_USEDEFAULT, CW_USEDEFAULT, 1440, 900, nullptr, nullptr, instance_, this);
    regularFont_ = CreateFontW(-15,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH|FF_DONTCARE,L"Microsoft YaHei UI");
    smallFont_ = CreateFontW(-13,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH|FF_DONTCARE,L"Microsoft YaHei UI");
    boldFont_ = CreateFontW(-15,0,0,0,FW_SEMIBOLD,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH|FF_DONTCARE,L"Microsoft YaHei UI");
    titleFont_ = CreateFontW(-28,0,0,0,FW_BOLD,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH|FF_DONTCARE,L"Microsoft YaHei UI");
}

void NativeApp::ClearControls() { for (HWND control : controls_) if (IsWindow(control)) DestroyWindow(control); controls_.clear(); byId_.clear(); }
void NativeApp::SetFont(HWND handle, bool bold, int size) { if (!handle) return; HFONT font = size <= 8 ? smallFont_ : (bold ? boldFont_ : regularFont_); SendMessageW(handle, WM_SETFONT, reinterpret_cast<WPARAM>(font), TRUE); }
HWND NativeApp::Button(int id, const std::wstring& text, int x, int y, int width, int height, DWORD extra) { HWND h = CreateWindowExW(0, L"BUTTON", text.c_str(), WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_FLAT | extra, x,y,width,height,window_,reinterpret_cast<HMENU>(static_cast<INT_PTR>(id)),instance_,nullptr); SetFont(h, false); controls_.push_back(h); byId_[id] = h; return h; }
HWND NativeApp::Edit(int id, const std::wstring& text, int x, int y, int width, int height, bool numeric) { DWORD style = WS_CHILD | WS_VISIBLE | WS_TABSTOP | WS_BORDER | ES_AUTOHSCROLL; if (numeric) style |= ES_NUMBER; HWND h = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", text.c_str(), style, x,y,width,height,window_,reinterpret_cast<HMENU>(static_cast<INT_PTR>(id)),instance_,nullptr); SetFont(h); controls_.push_back(h); byId_[id] = h; return h; }
HWND NativeApp::Combo(int id, const std::vector<std::wstring>& values, int selected, int x, int y, int width, int height) { HWND h = CreateWindowExW(0,L"COMBOBOX",L"",WS_CHILD|WS_VISIBLE|WS_TABSTOP|CBS_DROPDOWNLIST|WS_VSCROLL,x,y,width,height+130,window_,reinterpret_cast<HMENU>(static_cast<INT_PTR>(id)),instance_,nullptr); for (const auto& value:values) SendMessageW(h,CB_ADDSTRING,0,reinterpret_cast<LPARAM>(value.c_str())); SendMessageW(h,CB_SETCURSEL,selected,0); SetFont(h); controls_.push_back(h); byId_[id] = h; return h; }
HWND NativeApp::Label(const std::wstring& text, int x, int y, int width, int height, DWORD style) { HWND h = CreateWindowExW(0,L"STATIC",text.c_str(),WS_CHILD|WS_VISIBLE|style,x,y,width,height,window_,nullptr,instance_,nullptr); SetFont(h, false, 8); controls_.push_back(h); return h; }

void NativeApp::BuildManager() {
    screen_ = Screen::Manager; ClearControls(); InvalidateRect(window_,nullptr,TRUE); LoadManagerList();
    RECT r{}; GetClientRect(window_,&r); int center = (r.right-r.left)/2;
    Edit(IDC_CONFIG_NAME, L"新配置", center-240, 518, 260, 34);
    Button(IDC_CONFIG_NEW, L"新建配置", center+35, 518, 112, 34); Button(IDC_CONFIG_OPEN, L"打开选中", center+155, 518, 112, 34); Button(IDC_CONFIG_DELETE, L"删除", center+275, 518, 76, 34); Button(IDC_CONFIG_REFRESH, L"刷新", center+359, 518, 76, 34); Button(IDC_CONFIG_FORMULA, L"∑ 计算公式", center+250, 566, 120, 32);
    HWND list = CreateWindowExW(WS_EX_CLIENTEDGE,L"LISTBOX",L"",WS_CHILD|WS_VISIBLE|WS_TABSTOP|LBS_NOTIFY|WS_VSCROLL|LBS_NOINTEGRALHEIGHT,center-240,220,675,265,window_,reinterpret_cast<HMENU>(static_cast<INT_PTR>(IDC_CONFIG_LIST)),instance_,nullptr); SetFont(list); controls_.push_back(list); byId_[IDC_CONFIG_LIST]=list; LoadManagerList();
}
void NativeApp::LoadManagerList() {
    HWND list = Find(IDC_CONFIG_LIST); if (!list) return; SendMessageW(list,LB_RESETCONTENT,0,0); for (const auto& path : store_.List()) { std::wstring filename = path.stem().wstring(); SendMessageW(list,LB_ADDSTRING,0,reinterpret_cast<LPARAM>(filename.c_str())); }
}

void NativeApp::BuildMain() {
    screen_ = Screen::Main;
    ClearControls();
    Recalculate(false);
    RECT r{}; GetClientRect(window_, &r);
    const int width = r.right;
    const int height = r.bottom;
    const int right = width - kRightWidth;
    const int center = kLeftWidth + 18;
    const int centerWidth = right - kLeftWidth - 36;

    Button(IDC_NAV_MONSTER, L"盾  魔物设置", 20, 126, 212, 36);
    Button(IDC_NAV_CHARACTERS, L"人  角色", 20, 170, 184, 36);
    Button(IDC_ADD_CHARACTER, L"+", 206, 174, 28, 28);
    int listY = 214;
    for (size_t i = 0; i < config_.characters.size(); ++i) {
        Button(IDC_CHAR_BASE + static_cast<int>(i), ElementName(config_.characters[i].element) + L"   " + config_.characters[i].name,
               28, listY, 196, 32);
        listY += 36;
        if (listY > height - 170) break;
    }
    Button(IDC_NAV_HISTORY, L"▣  历史记录", 20, height - 104, 212, 36);
    Button(IDC_NAV_TIMELINE, L"◷  时间轴", 20, height - 58, 212, 36);

    // The island is a native command strip, not a browser overlay.
    islandExpanded_ = false;
    Button(IDC_ISLAND_SAVE, L"保存并退出", center + centerWidth - 410, 32, 84, 28);
    Button(IDC_ISLAND_DISCARD, L"不保存", center + centerWidth - 320, 32, 64, 28);
    Button(IDC_ISLAND_QUICK, L"快速拉表", center + centerWidth - 250, 32, 76, 28);
    Button(IDC_ISLAND_SETTINGS, L"设置", center + centerWidth - 168, 32, 52, 28);
    for (int id : {IDC_ISLAND_SAVE, IDC_ISLAND_DISCARD, IDC_ISLAND_QUICK, IDC_ISLAND_SETTINGS}) ShowWindow(Find(id), SW_HIDE);

    Button(IDC_TOOL_IMPORT, L"导入", right + 18, 30, 52, 28);
    Button(IDC_TOOL_EXPORT, L"导出", right + 76, 30, 52, 28);
    Button(IDC_TOOL_MORE, L"···", right + 134, 30, 52, 28);
    Button(IDC_TOOL_DETAILS, L"明细", right + 192, 30, 52, 28);
    Button(IDC_ADD_BASELINE, L"+ 设为新基准", right + 166, 128, 126, 26);
    if (config_.damageShareEnabled) Button(IDC_TOOL_SHARE, L"占比", right + 18, height - 142, 52, 28);

    const int top = 82;
    if (workspace_ == Workspace::Character) BuildCharacterControls(center, top, centerWidth);
    else if (workspace_ == Workspace::Monster) BuildMonsterControls(center, top, centerWidth);
    else if (workspace_ == Workspace::Timeline) BuildTimelineControls(center, top, centerWidth);
    else BuildHistoryControls(center, top, centerWidth);
    LayoutMain();
    InvalidateRect(window_, nullptr, TRUE);
}
void NativeApp::LayoutMain() {
    if (!IsMain()) return; RECT r{}; GetClientRect(window_,&r); int h=r.bottom, w=r.right; int right = w-kRightWidth; int centerWidth=right-kLeftWidth;
    // Native controls are deliberately laid out over a painted shell; no web surface or embedded document is used.
    if (Find(IDC_NAV_MONSTER)) { MoveWindow(Find(IDC_NAV_MONSTER),20,126,212,36,TRUE); MoveWindow(Find(IDC_NAV_CHARACTERS),20,170,184,36,TRUE); MoveWindow(Find(IDC_NAV_HISTORY),20,h-104,212,36,TRUE); MoveWindow(Find(IDC_NAV_TIMELINE),20,h-58,212,36,TRUE); MoveWindow(Find(IDC_ADD_CHARACTER),206,174,28,28,TRUE); }
}
void NativeApp::BuildCharacterControls(int left, int top, int width) {
    Character* c=CurrentCharacter(); if(!c) { Label(L"从左侧添加并选择角色",left+40,top+150,width-80,30); return; }
    Label(L"角色名称",left+34,top+76,80,24); Edit(IDC_CHAR_NAME,c->name,left+120,top+72,std::min(200,width-300),30);
    Label(L"元素",left+34,top+116,80,24); std::vector<std::wstring> elements={L"火 · Pyro",L"水 · Hydro",L"雷 · Electro",L"冰 · Cryo",L"草 · Dendro",L"风 · Anemo",L"岩 · Geo",L"物理"}; std::vector<std::string> keys={"pyro","hydro","electro","cryo","dendro","anemo","geo","physical"}; int es=static_cast<int>(std::find(keys.begin(),keys.end(),c->element)-keys.begin()); Combo(IDC_CHAR_ELEMENT,elements,es,left+120,112,155,28);
    Label(L"等级",left+292,top+116,42,24); Edit(IDC_CHAR_LEVEL,Number(c->level),left+334,top+112,70,30,true); Button(IDC_CHAR_DELETE,L"删除角色",left+width-130,top+72,96,30);
    Label(L"基础攻击",left+34,top+166,80,24); Edit(IDC_CHAR_BASE_ATK,Number(c->baseAtk,1),left+120,top+162,100,30,true); Label(L"武器攻击",left+234,top+166,80,24); Edit(IDC_CHAR_WEAPON_ATK,Number(c->weaponAtk,1),left+320,top+162,100,30,true); Label(L"攻击力 %",left+434,top+166,65,24); Edit(IDC_CHAR_ATK_PCT,Number(c->atkPct,1),left+500,top+162,80,30,true);
    Label(L"生命值",left+34,top+206,80,24); Edit(IDC_CHAR_BASE_HP,Number(c->baseHp,1),left+120,top+202,100,30,true); Label(L"元素精通",left+234,top+206,80,24); Edit(IDC_CHAR_EM,Number(c->em,1),left+320,top+202,100,30,true); Label(L"暴击率 / 伤害",left+434,top+206,92,24); Edit(IDC_CHAR_CRIT,Number(c->critRate,1),left+528,top+202,70,30,true); Edit(IDC_CHAR_CD,Number(c->critDmg,1),left+604,top+202,70,30,true);
    Label(L"伤害来源",left+34,top+260,130,26); Button(IDC_ADD_SOURCE,L"＋ 添加伤害来源",left+width-170,top+254,136,30);
    int y=top+300; for(size_t i=0;i<c->damageSources.size();++i) { const auto& s=c->damageSources[i]; int base=IDC_SOURCE_BASE+static_cast<int>(i)*10; Label(s.type+L"  ·  "+ElementName(s.element),left+34,y,150,24); Edit(base+1,s.name,left+185,y-3,std::min(240,width-450),28); Edit(base+2,Number(s.multiplier,1),left+430,y-3,72,28,true); Button(base+3,s.enabled?L"已启用":L"已停用",left+510,y-3,72,28); Button(base+4,L"删除",left+588,y-3,54,28); y+=42; }
    Label(L"倍率（%） · 暴击期望值按当前面板即时计算。双击配置名或退出前均会自动保存。",left+34,y+12,width-70,24);
}
void NativeApp::BuildMonsterControls(int left, int top, int width) {
    Label(L"TARGET CONFIGURATION",left+34,top+70,width-68,22); Label(L"魔物设置",left+34,top+98,width-68,40); Label(L"设置目标等级与各元素抗性，所有伤害来源会即时按目标重新结算。",left+34,top+140,width-68,30);
    Label(L"魔物等级",left+34,top+202,90,24); Edit(IDC_MONSTER_LEVEL,Number(config_.enemyLevel),left+132,top+198,110,30,true);
    int y=top+258; std::vector<std::string> keys={"pyro","hydro","electro","cryo","dendro","anemo","geo","physical"}; for(size_t i=0;i<keys.size();++i) { int col=static_cast<int>(i%2), row=static_cast<int>(i/2); int x=left+34+col*(width/2-22); Label(ElementName(keys[i])+L" 抗性 %",x,y+row*48,112,25); Edit(IDC_RES_BASE+static_cast<int>(i),Number(config_.enemyResistance[keys[i]],1),x+118,y+row*48,width/2-150,28,true); }
}
void NativeApp::BuildTimelineControls(int left, int top, int width) {
    Label(L"ROTATION TIMELINE",left+34,top+70,width-68,22); Label(L"循环时间轴",left+34,top+98,width-68,40); Label(L"查看角色伤害来源在循环内的释放位置与持续区间。",left+34,top+140,width-68,30);
    Label(L"轴长（秒）",left+34,top+202,92,24); Edit(IDC_ROTATION,Number(config_.rotationDuration,1),left+132,top+198,100,30,true); Button(IDC_TIMELINE_TOGGLE,config_.timelineEnabled?L"时间轴：已开启":L"时间轴：已关闭",left+250,top+198,150,30);
    int y=top+270; for (size_t i=0;i<config_.characters.size();++i) { const auto& c=config_.characters[i]; Label(c.name+L"  ·  "+ElementName(c.element),left+42,y+static_cast<int>(i)*42,190,25); int bar=static_cast<int>(std::min(1.0,calculation_.characterTotals.count(c.id)?calculation_.characterTotals[c.id]/std::max(1.0,calculation_.total):0.0)*std::max(140,width-350)); HWND unused=nullptr; (void)unused; Label(L"■",left+250,y+static_cast<int>(i)*42,bar,25); Label(L"伤害  "+Total(calculation_.characterTotals.count(c.id)?calculation_.characterTotals[c.id]:0),left+260+bar,y+static_cast<int>(i)*42,140,25); }
}
void NativeApp::BuildHistoryControls(int left, int top, int width) {
    Label(L"HISTORY",left+34,top+70,width-68,22); Label(L"历史记录",left+34,top+98,width-68,40); Label(L"页面关闭与完成快速拉表时自动保存当前配置和结果。",left+34,top+140,width-68,30);
    int y=top+216; if(config_.history.empty()) Label(L"暂无历史记录",left+34,y,width-68,32); for(const auto& item:config_.history){ Label(L"●  "+item,left+42,y,width-80,30); y+=38; }
}

void NativeApp::OnCommand(WPARAM wParam, LPARAM lParam) {
    int id=LOWORD(wParam), notification=HIWORD(wParam); HWND source=reinterpret_cast<HWND>(lParam);
    if (screen_==Screen::Manager) {
        if(id==IDC_CONFIG_FORMULA){ShowFormula();return;} if(id==IDC_CONFIG_NEW){NewConfig();return;} if(id==IDC_CONFIG_OPEN){OpenSelectedConfig();return;} if(id==IDC_CONFIG_DELETE){int sel=static_cast<int>(SendMessageW(Find(IDC_CONFIG_LIST),LB_GETCURSEL,0,0)); if(sel>=0){wchar_t text[260]{}; SendMessageW(Find(IDC_CONFIG_LIST),LB_GETTEXT,sel,reinterpret_cast<LPARAM>(text)); ConfigStore s(store_.dateDirectory().parent_path()); s.Remove(store_.PathFor(text)); LoadManagerList(); InvalidateRect(window_,nullptr,TRUE);} return;} if(id==IDC_CONFIG_REFRESH){LoadManagerList();return;} if(id==IDC_CONFIG_LIST && notification==LBN_DBLCLK){OpenSelectedConfig();return;} return;
    }
    if(id==IDC_NAV_MONSTER){SetWorkspace(Workspace::Monster);return;} if(id==IDC_NAV_CHARACTERS){SetWorkspace(Workspace::Character);return;} if(id==IDC_NAV_TIMELINE){SetWorkspace(Workspace::Timeline);return;} if(id==IDC_NAV_HISTORY){SetWorkspace(Workspace::History);return;} if(id==IDC_ADD_CHARACTER){AddCharacter();return;}
    if(id>=IDC_CHAR_BASE && id<IDC_CHAR_BASE+100){SelectCharacter(static_cast<size_t>(id-IDC_CHAR_BASE));return;}
    if(id==IDC_ISLAND_SAVE){SaveConfig(true);return;} if(id==IDC_ISLAND_DISCARD){LeaveWithoutSaving();return;} if(id==IDC_ISLAND_QUICK){ShowQuickTable();return;} if(id==IDC_ISLAND_SETTINGS){ShowSettings();return;}
    if(id==IDC_TOOL_IMPORT){ImportConfig();return;} if(id==IDC_TOOL_EXPORT){ExportConfig();return;} if(id==IDC_TOOL_MORE){int choice=MessageBoxW(window_,L"更多操作\n\n点击“是”打开全局设置，点击“否”重置当前配置。",L"更多",MB_YESNOCANCEL|MB_ICONINFORMATION);if(choice==IDYES)ShowSettings();else if(choice==IDNO)ResetConfig();return;} if(id==IDC_TOOL_FORMULA){ShowFormula();return;} if(id==IDC_TOOL_DETAILS){ShowDetails();return;} if(id==IDC_TOOL_SHARE){ShowShare();return;}
    if(id==IDC_ADD_SOURCE){AddSource();return;} if(id==IDC_ADD_BASELINE){Baseline baseline;baseline.id=NewId();baseline.name=L"基准 "+Number(static_cast<double>(config_.baselines.size()+1));baseline.total=calculation_.total;config_.baselines.push_back(baseline);Recalculate();return;} if(id==IDC_CHAR_DELETE){if(config_.characters.size()>1){config_.characters.erase(config_.characters.begin()+selectedCharacter_);selectedCharacter_=std::min(selectedCharacter_,config_.characters.size()-1);BuildMain();}return;}
    if(id==IDC_TIMELINE_TOGGLE){config_.timelineEnabled=!config_.timelineEnabled; BuildMain();return;} if(id==IDC_SAVE_SETTINGS){SaveConfig(false);return;}
    if(id==IDC_MONSTER_LEVEL && (notification==EN_CHANGE||notification==EN_KILLFOCUS)){config_.enemyLevel=std::clamp(static_cast<int>(EditNumber(id,93)),1,120);Recalculate();return;} if(id==IDC_ROTATION && (notification==EN_CHANGE||notification==EN_KILLFOCUS)){config_.rotationDuration=std::max(1.0,EditNumber(id,20));Recalculate();return;}
    if(id>=IDC_RES_BASE && id<IDC_RES_BASE+8 && (notification==EN_CHANGE||notification==EN_KILLFOCUS)){static const char* keys[]={"pyro","hydro","electro","cryo","dendro","anemo","geo","physical"};config_.enemyResistance[keys[id-IDC_RES_BASE]]=EditNumber(id,10);Recalculate();return;}
    if(id==IDC_CHAR_NAME && notification==EN_CHANGE){if(auto*c=CurrentCharacter()){c->name=EditText(id);if(HWND item=Find(IDC_CHAR_BASE+static_cast<int>(selectedCharacter_)))SetWindowTextW(item,(ElementName(c->element)+L"   "+c->name).c_str());}Recalculate();return;} if(id==IDC_CHAR_LEVEL && (notification==EN_CHANGE||notification==EN_KILLFOCUS)){if(auto*c=CurrentCharacter())c->level=std::clamp(static_cast<int>(EditNumber(id,90)),1,100);Recalculate();return;} if(id==IDC_CHAR_BASE_ATK && (notification==EN_CHANGE||notification==EN_KILLFOCUS)){if(auto*c=CurrentCharacter())c->baseAtk=EditNumber(id);Recalculate();return;} if(id==IDC_CHAR_BASE_HP && (notification==EN_CHANGE||notification==EN_KILLFOCUS)){if(auto*c=CurrentCharacter())c->baseHp=EditNumber(id);Recalculate();return;} if(id==IDC_CHAR_WEAPON_ATK && (notification==EN_CHANGE||notification==EN_KILLFOCUS)){if(auto*c=CurrentCharacter())c->weaponAtk=EditNumber(id);Recalculate();return;} if(id==IDC_CHAR_ATK_PCT && (notification==EN_CHANGE||notification==EN_KILLFOCUS)){if(auto*c=CurrentCharacter())c->atkPct=EditNumber(id);Recalculate();return;} if(id==IDC_CHAR_EM && (notification==EN_CHANGE||notification==EN_KILLFOCUS)){if(auto*c=CurrentCharacter())c->em=EditNumber(id);Recalculate();return;} if(id==IDC_CHAR_CRIT && (notification==EN_CHANGE||notification==EN_KILLFOCUS)){if(auto*c=CurrentCharacter())c->critRate=EditNumber(id);Recalculate();return;} if(id==IDC_CHAR_CD && (notification==EN_CHANGE||notification==EN_KILLFOCUS)){if(auto*c=CurrentCharacter())c->critDmg=EditNumber(id);Recalculate();return;}
    if(id==IDC_CHAR_ELEMENT && notification==CBN_SELCHANGE){if(auto*c=CurrentCharacter()){static const char* keys[]={"pyro","hydro","electro","cryo","dendro","anemo","geo","physical"};c->element=keys[static_cast<int>(SendMessageW(source,CB_GETCURSEL,0,0))];for(auto&d:c->damageSources)d.element=c->element;Recalculate();}return;}
    if(id>=IDC_SOURCE_BASE && id<IDC_SOURCE_BASE+1000){int relative=id-IDC_SOURCE_BASE;size_t sourceIndex=static_cast<size_t>(relative/10);int field=relative%10;Character*c=CurrentCharacter();if(!c||sourceIndex>=c->damageSources.size())return;DamageSource&d=c->damageSources[sourceIndex];if(field==1&&notification==EN_CHANGE)d.name=EditText(id);if(field==2&&(notification==EN_CHANGE||notification==EN_KILLFOCUS))d.multiplier=EditNumber(id,100);if(field==3&&notification==BN_CLICKED){d.enabled=!d.enabled;BuildMain();return;}if(field==4&&notification==BN_CLICKED){c->damageSources.erase(c->damageSources.begin()+sourceIndex);BuildMain();return;}Recalculate();return;}
}

void NativeApp::SetWorkspace(Workspace workspace) { workspace_=workspace; moreMenu_=false; BuildMain(); }
void NativeApp::SelectCharacter(size_t index) { if(index>=config_.characters.size())return; selectedCharacter_=index; workspace_=Workspace::Character; BuildMain(); }
void NativeApp::AddCharacter() { static const char* presets[]={"hutao","yelan","raiden","nahida","furina","bennett"}; config_.characters.push_back(MakePreset(presets[config_.characters.size()%6])); selectedCharacter_=config_.characters.size()-1; workspace_=Workspace::Character; BuildMain(); }
void NativeApp::AddSource() { if(auto*c=CurrentCharacter()){DamageSource s;s.id=NewId();s.name=L"新伤害来源";s.type=L"元素战技";s.element=c->element;s.multiplier=100;c->damageSources.push_back(s);BuildMain();} }
Character* NativeApp::CurrentCharacter() { return selectedCharacter_<config_.characters.size()?&config_.characters[selectedCharacter_]:nullptr; }
const Character* NativeApp::CurrentCharacter() const { return selectedCharacter_<config_.characters.size()?&config_.characters[selectedCharacter_]:nullptr; }
void NativeApp::Recalculate(bool repaint) { calculation_=Calculate(config_); if(repaint)InvalidateRect(window_,nullptr,TRUE); }

void NativeApp::NewConfig() { std::wstring name=EditText(IDC_CONFIG_NAME); if(name.empty())name=L"新配置"; config_=MakeDefaultConfig(name);savedConfig_=config_;currentPath_=store_.PathFor(name);store_.Save(config_,currentPath_);selectedCharacter_=0;workspace_=Workspace::Character;BuildMain(); }
void NativeApp::OpenSelectedConfig() { HWND list=Find(IDC_CONFIG_LIST);if(!list)return;int sel=static_cast<int>(SendMessageW(list,LB_GETCURSEL,0,0));if(sel<0){MessageBoxW(window_,L"请先选择一个配置。",L"Gi DMG",MB_OK|MB_ICONINFORMATION);return;}wchar_t text[260]{};SendMessageW(list,LB_GETTEXT,sel,reinterpret_cast<LPARAM>(text));Config loaded;if(!store_.Load(store_.PathFor(text),loaded)){MessageBoxW(window_,L"配置文件无法读取，可能已损坏。",L"Gi DMG",MB_OK|MB_ICONERROR);return;}config_=std::move(loaded);savedConfig_=config_;currentPath_=store_.PathFor(text);selectedCharacter_=0;workspace_=Workspace::Character;BuildMain();}
void NativeApp::SaveConfig(bool leave) { UpdateSelectedFromControls(); Recalculate(false); if(currentPath_.empty())currentPath_=store_.PathFor(config_.name); store_.Save(config_,currentPath_);AppendHistory();store_.Save(config_,currentPath_);savedConfig_=config_;if(leave)BuildManager();else InvalidateRect(window_,nullptr,TRUE); }
void NativeApp::LeaveWithoutSaving() { config_=savedConfig_;BuildManager(); }
void NativeApp::AppendHistory() { std::wstring entry=Number(calculation_.total)+L" · "+config_.name;config_.history.insert(config_.history.begin(),entry);if(config_.history.size()>20)config_.history.resize(20); }
void NativeApp::UpdateSelectedFromControls() { if(!CurrentCharacter())return; Character*c=CurrentCharacter(); c->name=EditText(IDC_CHAR_NAME); if(!EditText(IDC_CHAR_LEVEL).empty()) c->level=std::clamp(static_cast<int>(EditNumber(IDC_CHAR_LEVEL, c->level)), 1, 100); }

void NativeApp::ShowSettings() { std::wstring text=L"全局设置\n\n循环时间轴："+(config_.timelineEnabled?std::wstring(L"已开启"):L"已关闭")+L"\n伤害占比："+(config_.damageShareEnabled?std::wstring(L"已开启"):L"已关闭")+L"\n循环总轴长："+Number(config_.rotationDuration,1)+L" 秒\n\n点击“是”切换循环时间轴，点击“否”只关闭此窗口。";if(MessageBoxW(window_,text.c_str(),L"全局设置",MB_YESNO|MB_ICONINFORMATION)==IDYES){config_.timelineEnabled=!config_.timelineEnabled;BuildMain();}}
void NativeApp::ShowFormula() { std::wstring text=L"伤害计算公式（原生引擎）\n\n直伤 = 面板属性 × 技能倍率 × 暴击期望 × 元素伤害加成 × 防御区 × 抗性区\n反应伤害按角色等级、元素精通、反应倍率独立结算。\n\n防御区 = (100 + 角色等级) / (100 + 角色等级 + 魔物等级)\n抗性区按负抗性、常规抗性与高抗性分段计算。\n\n当前总期望："+Total(calculation_.total)+L"\n当前 DPS："+Total(calculation_.dps)+L" / 秒";MessageBoxW(window_,text.c_str(),L"计算公式",MB_OK|MB_ICONINFORMATION);}
void NativeApp::ShowQuickTable() { std::wstring text=L"快速拉表\n\n当前配置："+config_.name+L"\n组合数量："+Number(static_cast<double>(config_.characters.size()))+L" 个角色\n总期望伤害："+Total(calculation_.total)+L"\n全队 DPS："+Total(calculation_.dps)+L" / 秒\n\n原生版本的拉表入口会保留当前配置并将结果写入历史记录。";MessageBoxW(window_,text.c_str(),L"快速拉表",MB_OK|MB_ICONINFORMATION);SaveConfig(false);}
void NativeApp::ShowDetails() { std::wstring text=L"面板明细\n\n";if(auto*c=CurrentCharacter()){double atk=(c->baseAtk+c->weaponAtk)*(1+c->atkPct/100)+c->atkFlat;double hp=c->baseHp*(1+c->hpPct/100)+c->hpFlat;text+=c->name+L"\n攻击力："+Number(atk)+L"\n生命值："+Number(hp)+L"\n元素精通："+Number(c->em)+L"\n暴击率："+Number(c->critRate,1)+L"%\n暴击伤害："+Number(c->critDmg,1)+L"%";}MessageBoxW(window_,text.c_str(),L"面板明细",MB_OK|MB_ICONINFORMATION);}
void NativeApp::ShowShare() { std::wstring text=L"角色伤害占比\n\n";for(const auto&c:config_.characters){double d=calculation_.characterTotals.count(c.id)?calculation_.characterTotals.at(c.id):0;text+=c.name+L"  "+Number(d)+L"  ("+Number(calculation_.total?d/calculation_.total*100:0,1)+L"%)\n";}MessageBoxW(window_,text.c_str(),L"角色伤害占比",MB_OK|MB_ICONINFORMATION);}
void NativeApp::ResetConfig() { if(MessageBoxW(window_,L"清空当前配置中的角色、基准和历史记录？",L"重置配置",MB_YESNO|MB_ICONWARNING)==IDYES){config_.characters.clear();config_.baselines.clear();config_.history.clear();selectedCharacter_=0;BuildMain();} }
void NativeApp::ImportConfig() { OPENFILENAMEW dialog{sizeof(dialog)};wchar_t path[MAX_PATH]{};dialog.hwndOwner=window_;dialog.lpstrFilter=L"Gi DMG 配置 (*.json)\0*.json\0所有文件\0*.*\0";dialog.lpstrFile=path;dialog.nMaxFile=MAX_PATH;dialog.Flags=OFN_FILEMUSTEXIST|OFN_PATHMUSTEXIST;if(GetOpenFileNameW(&dialog)){Config loaded;if(store_.Load(path,loaded)){config_=std::move(loaded);savedConfig_=config_;selectedCharacter_=0;Recalculate();BuildMain();}else MessageBoxW(window_,L"导入失败：不是有效的 Gi DMG 配置。",L"导入配置",MB_OK|MB_ICONERROR);}}
void NativeApp::ExportConfig() { OPENFILENAMEW dialog{sizeof(dialog)};wchar_t path[MAX_PATH]=L"Gi DMG 配置.json";dialog.hwndOwner=window_;dialog.lpstrFilter=L"Gi DMG 配置 (*.json)\0*.json\0";dialog.lpstrFile=path;dialog.nMaxFile=MAX_PATH;dialog.Flags=OFN_OVERWRITEPROMPT; if(GetSaveFileNameW(&dialog)){UpdateSelectedFromControls();Recalculate(false);if(!store_.Save(config_,path))MessageBoxW(window_,L"导出失败。",L"导出配置",MB_OK|MB_ICONERROR);}}

HWND NativeApp::Find(int id) const { auto it=byId_.find(id);return it==byId_.end()?nullptr:it->second; }
std::wstring NativeApp::EditText(int id) const { HWND h=Find(id);if(!h)return {};int n=GetWindowTextLengthW(h);std::wstring value(static_cast<size_t>(n)+1,L'\0');GetWindowTextW(h,value.data(),n+1);value.resize(static_cast<size_t>(n));return value; }
double NativeApp::EditNumber(int id,double fallback) const { try{auto text=EditText(id);return text.empty()?fallback:std::stod(text);}catch(...){return fallback;} }
void NativeApp::SetText(int id,const std::wstring& text){if(HWND h=Find(id))SetWindowTextW(h,text.c_str());}

void NativeApp::Paint(HDC dc) { RECT client{};GetClientRect(window_,&client);if(screen_==Screen::Manager)PaintManager(dc,client);else PaintMain(dc,client); }
void NativeApp::Fill(HDC dc,RECT rect,COLORREF color){HBRUSH brush=CreateSolidBrush(color);FillRect(dc,&rect,brush);DeleteObject(brush);}
void NativeApp::Round(HDC dc,RECT rect,COLORREF fill,COLORREF border,int radius){HBRUSH brush=CreateSolidBrush(fill);HPEN pen=CreatePen(PS_SOLID,1,border);auto oldBrush=SelectObject(dc,brush);auto oldPen=SelectObject(dc,pen);RoundRect(dc,rect.left,rect.top,rect.right,rect.bottom,radius,radius);SelectObject(dc,oldBrush);SelectObject(dc,oldPen);DeleteObject(brush);DeleteObject(pen);}
void NativeApp::DrawTextLine(HDC dc,const std::wstring& text,RECT rect,COLORREF color,int size,bool bold,UINT format){SetBkMode(dc,TRANSPARENT);SetTextColor(dc,color);HFONT font=size>=18?titleFont_:(bold?boldFont_:smallFont_);auto old=SelectObject(dc,font);DrawTextW(dc,text.c_str(),-1,&rect,format|DT_NOPREFIX);SelectObject(dc,old);}
void NativeApp::PaintManager(HDC dc,const RECT& client){Fill(dc,client,RGB(243,245,248));int cx=client.right/2;DrawTextLine(dc,L"DAMAGE CALCULATOR LAB",{cx-300,84,cx+300,108},RGB(164,135,98),9,true,DT_CENTER);DrawTextLine(dc,L"伤害计算实验室",{cx-320,122,cx+320,172},RGB(43,47,54),30,true,DT_CENTER);DrawTextLine(dc,L"原生单 EXE 配置管理",{cx-320,178,cx+320,208},RGB(91,100,112),10,false,DT_CENTER);Round(dc,{cx-260,210,cx+260,620},RGB(255,255,255),RGB(226,229,235),20);DrawTextLine(dc,L"配置",{cx-222,238,cx+222,270},RGB(43,47,54),16,true);DrawTextLine(dc,L"配置文件保存在程序同目录的 date 文件夹中",{cx-222,274,cx+222,300},RGB(91,100,112),9);DrawTextLine(dc,L"双击列表项或点击“打开选中”进入计算器",{cx-222,300,cx+222,326},RGB(125,133,144),9);DrawTextLine(dc,L"点击新建配置即可生成带胡桃示例的计算配置",{cx-222,458,cx+222,480},RGB(125,133,144),9);}
void NativeApp::PaintMain(HDC dc,const RECT& client){int w=client.right,h=client.bottom;int right=w-kRightWidth;Fill(dc,client,RGB(243,245,248));Fill(dc,{0,0,kLeftWidth,h},RGB(255,255,255));Fill(dc,{right,0,w,h},RGB(255,255,255));HPEN divider=CreatePen(PS_SOLID,1,RGB(226,229,235));auto old=SelectObject(dc,divider);MoveToEx(dc,kLeftWidth,0,nullptr);LineTo(dc,kLeftWidth,h);MoveToEx(dc,right,0,nullptr);LineTo(dc,right,h);SelectObject(dc,old);DeleteObject(divider);
    DrawTextLine(dc,L"Gi DMG",{24,22,220,52},RGB(43,47,54),16,true);DrawTextLine(dc,L"原神伤害计算器  ·  v2.2.0",{24,50,230,72},RGB(91,100,112),8);
    // Sidebar character entries are drawn so the shell remains readable even while native buttons are focused.
    DrawTextLine(dc,L"计算器导航",{24,94,228,116},RGB(125,133,144),8,true);int y=214;for(size_t i=0;i<config_.characters.size();++i){if(i==selectedCharacter_&&workspace_==Workspace::Character)Round(dc,{14,y-4,238,y+34},RGB(237,243,255),RGB(199,216,247),9);DrawTextLine(dc,ElementName(config_.characters[i].element),{34,y,60,y+28},ElementColor(config_.characters[i].element),9,true,DT_CENTER);DrawTextLine(dc,config_.characters[i].name,{68,y,210,y+28},RGB(79,89,102),9,true);y+=36;if(y>h-150)break;}
    int center=kLeftWidth+18;int centerWidth=right-kLeftWidth-36;Round(dc,{center,18,right-18,68},RGB(255,255,255),RGB(226,229,235),18);DrawTextLine(dc,config_.name.empty()?L"未命名配置":config_.name,{center+20,25,right-240,61},RGB(43,47,54),10,true);DrawTextLine(dc,islandExpanded_?L"保存并退出   ·   不保存   ·   快速拉表   ·   设置":L"移入顶部展开操作",{right-420,25,right-38,61},RGB(91,100,112),8,false,DT_RIGHT);
    int top=82;Round(dc,{center,top,right-18,h-18},RGB(255,255,255),RGB(226,229,235),18);
    if(workspace_==Workspace::Character){DrawTextLine(dc,L"角色配置",{center+34,top+24,right-40,top+56},RGB(43,47,54),17,true);if(CurrentCharacter())DrawTextLine(dc,CurrentCharacter()->name+L"  ·  "+ElementName(CurrentCharacter()->element),{center+34,top+52,right-40,top+75},ElementColor(CurrentCharacter()->element),9,true);}else if(workspace_==Workspace::Monster){DrawTextLine(dc,L"魔物设置",{center+34,top+24,right-40,top+58},RGB(43,47,54),17,true);}else if(workspace_==Workspace::Timeline){DrawTextLine(dc,L"循环时间轴",{center+34,top+24,right-40,top+58},RGB(43,47,54),17,true);}else{DrawTextLine(dc,L"历史记录",{center+34,top+24,right-40,top+58},RGB(43,47,54),17,true);}
    int rightX=right+18;DrawTextLine(dc,L"伤害统计",{rightX+18,88,rightX+290,120},RGB(43,47,54),16,true);DrawTextLine(dc,L"基准值",{rightX+18,132,rightX+290,158},RGB(91,100,112),9,true);DrawTextLine(dc,L"当前配置",{rightX+18,166,rightX+150,190},RGB(91,100,112),9);DrawTextLine(dc,Total(calculation_.total),{rightX+180,158,rightX+290,194},RGB(43,47,54),16,true,DT_RIGHT);DrawTextLine(dc,L"伤害来源",{rightX+18,220,rightX+290,246},RGB(91,100,112),9,true);
    int ry=252;int count=0;for(const auto&s:calculation_.sources){Round(dc,{rightX+18,ry,rightX+290,ry+58},RGB(248,249,251),RGB(226,229,235),9);DrawTextLine(dc,s.character,{rightX+30,ry+8,rightX+155,ry+30},RGB(43,47,54),9,true);DrawTextLine(dc,s.name,{rightX+30,ry+30,rightX+180,ry+49},RGB(91,100,112),8);DrawTextLine(dc,Total(s.value),{rightX+170,ry+13,rightX+278,ry+38},RGB(11,87,208),11,true,DT_RIGHT);ry+=66;if(++count>=5)break;}
    Fill(dc,{rightX+18,h-104,rightX+290,h-103},RGB(226,229,235));DrawTextLine(dc,L"总期望伤害",{rightX+18,h-90,rightX+170,h-64},RGB(91,100,112),9);DrawTextLine(dc,Total(calculation_.total),{rightX+160,h-98,rightX+290,h-58},RGB(43,47,54),18,true,DT_RIGHT);DrawTextLine(dc,L"全队 DPS   "+Total(calculation_.dps)+L" / 秒",{rightX+18,h-52,rightX+290,h-25},RGB(11,87,208),9,true,DT_RIGHT);
    if(moreMenu_)Round(dc,{rightX+82,56,rightX+290,190},RGB(255,255,255),RGB(226,229,235),10);
}

void NativeApp::OnMouseMove(int x,int y){lastMouse_={x,y};if(IsMain()){bool overIsland=(y<85&&x>=kLeftWidth);if(overIsland!=islandExpanded_){islandExpanded_=overIsland;for(int id:{IDC_ISLAND_SAVE,IDC_ISLAND_DISCARD,IDC_ISLAND_QUICK,IDC_ISLAND_SETTINGS})if(HWND item=Find(id))ShowWindow(item,islandExpanded_?SW_SHOW:SW_HIDE);InvalidateRect(window_,nullptr,FALSE);}}}
LRESULT CALLBACK NativeApp::WindowProc(HWND hwnd,UINT message,WPARAM wParam,LPARAM lParam){NativeApp*app=reinterpret_cast<NativeApp*>(GetWindowLongPtrW(hwnd,GWLP_USERDATA));if(message==WM_NCCREATE){auto*create=reinterpret_cast<CREATESTRUCTW*>(lParam);app=static_cast<NativeApp*>(create->lpCreateParams);SetWindowLongPtrW(hwnd,GWLP_USERDATA,reinterpret_cast<LONG_PTR>(app));g_app=app;app->window_=hwnd;}if(!app)return DefWindowProcW(hwnd,message,wParam,lParam);switch(message){case WM_COMMAND:app->OnCommand(wParam,lParam);return 0;case WM_MOUSEMOVE:app->OnMouseMove(GET_X_LPARAM(lParam),GET_Y_LPARAM(lParam));return 0;case WM_SIZE:app->LayoutMain();InvalidateRect(hwnd,nullptr,FALSE);return 0;case WM_GETMINMAXINFO:{auto*info=reinterpret_cast<MINMAXINFO*>(lParam);info->ptMinTrackSize.x=1180;info->ptMinTrackSize.y=720;return 0;}case WM_ERASEBKGND:return 1;case WM_PAINT:{PAINTSTRUCT ps;HDC dc=BeginPaint(hwnd,&ps);app->Paint(dc);EndPaint(hwnd,&ps);return 0;}case WM_CTLCOLORSTATIC:{HDC dc=reinterpret_cast<HDC>(wParam);SetBkMode(dc,TRANSPARENT);SetTextColor(dc,RGB(79,89,102));return reinterpret_cast<LRESULT>(GetStockObject(NULL_BRUSH));}case WM_CTLCOLOREDIT:{HDC dc=reinterpret_cast<HDC>(wParam);SetBkColor(dc,RGB(255,255,255));SetTextColor(dc,RGB(43,47,54));return reinterpret_cast<LRESULT>(GetStockObject(WHITE_BRUSH));}case WM_CLOSE:if(app->screen_==Screen::Main){app->SaveConfig(false);}DestroyWindow(hwnd);return 0;case WM_DESTROY:PostQuitMessage(0);return 0;}return DefWindowProcW(hwnd,message,wParam,lParam);}

} // namespace

int WINAPI wWinMain(HINSTANCE instance,HINSTANCE,LPWSTR,int){SetProcessDPIAware();NativeApp app(instance);return app.Run();}
