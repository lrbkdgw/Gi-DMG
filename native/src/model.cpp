#include "model.h"

#include <algorithm>
#include <chrono>
#include <climits>
#include <cmath>
#include <cstdlib>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <random>
#include <sstream>
#include <utility>

namespace gidmg {
namespace {

struct JsonValue {
    enum class Kind { Null, Bool, Number, String, Object, Array } kind = Kind::Null;
    bool boolean = false;
    double number = 0.0;
    std::string string;
    std::map<std::string, JsonValue> object;
    std::vector<JsonValue> array;

    static JsonValue String(const std::string& value) { JsonValue v; v.kind = Kind::String; v.string = value; return v; }
    static JsonValue Number(double value) { JsonValue v; v.kind = Kind::Number; v.number = value; return v; }
    static JsonValue Bool(bool value) { JsonValue v; v.kind = Kind::Bool; v.boolean = value; return v; }
    static JsonValue Object() { JsonValue v; v.kind = Kind::Object; return v; }
    static JsonValue Array() { JsonValue v; v.kind = Kind::Array; return v; }
};

class JsonParser {
public:
    explicit JsonParser(std::string source) : source_(std::move(source)) {}
    bool Parse(JsonValue& value) {
        Skip();
        if (!Value(value)) return false;
        Skip();
        return at_ == source_.size();
    }
private:
    void Skip() { while (at_ < source_.size() && static_cast<unsigned char>(source_[at_]) <= 32) ++at_; }
    bool Take(char c) { Skip(); if (at_ >= source_.size() || source_[at_] != c) return false; ++at_; return true; }
    bool Value(JsonValue& value) {
        Skip();
        if (at_ >= source_.size()) return false;
        switch (source_[at_]) {
        case '{': return Object(value);
        case '[': return Array(value);
        case '"': value.kind = JsonValue::Kind::String; return String(value.string);
        case 't': if (source_.compare(at_, 4, "true") == 0) { at_ += 4; value = JsonValue::Bool(true); return true; } return false;
        case 'f': if (source_.compare(at_, 5, "false") == 0) { at_ += 5; value = JsonValue::Bool(false); return true; } return false;
        case 'n': if (source_.compare(at_, 4, "null") == 0) { at_ += 4; value.kind = JsonValue::Kind::Null; return true; } return false;
        default: return Number(value);
        }
    }
    bool String(std::string& out) {
        if (!Take('"')) return false;
        out.clear();
        while (at_ < source_.size()) {
            char c = source_[at_++];
            if (c == '"') return true;
            if (c != '\\') { out.push_back(c); continue; }
            if (at_ >= source_.size()) return false;
            char escaped = source_[at_++];
            switch (escaped) {
            case '"': out.push_back('"'); break;
            case '\\': out.push_back('\\'); break;
            case '/': out.push_back('/'); break;
            case 'b': out.push_back('\b'); break;
            case 'f': out.push_back('\f'); break;
            case 'n': out.push_back('\n'); break;
            case 'r': out.push_back('\r'); break;
            case 't': out.push_back('\t'); break;
            case 'u': {
                // UTF-8 is emitted by the writer. Accepting ASCII \\u escapes keeps
                // the importer friendly to hand-edited files; non-ASCII escapes are
                // intentionally copied as UTF-8 bytes after a conservative decode.
                if (at_ + 4 > source_.size()) return false;
                unsigned codepoint = 0;
                for (int i = 0; i < 4; ++i) {
                    char h = source_[at_++]; codepoint <<= 4;
                    if (h >= '0' && h <= '9') codepoint += h - '0';
                    else if (h >= 'a' && h <= 'f') codepoint += h - 'a' + 10;
                    else if (h >= 'A' && h <= 'F') codepoint += h - 'A' + 10;
                    else return false;
                }
                if (codepoint < 0x80) out.push_back(static_cast<char>(codepoint));
                else if (codepoint < 0x800) { out.push_back(static_cast<char>(0xC0 | (codepoint >> 6))); out.push_back(static_cast<char>(0x80 | (codepoint & 0x3F))); }
                else { out.push_back(static_cast<char>(0xE0 | (codepoint >> 12))); out.push_back(static_cast<char>(0x80 | ((codepoint >> 6) & 0x3F))); out.push_back(static_cast<char>(0x80 | (codepoint & 0x3F))); }
                break;
            }
            default: return false;
            }
        }
        return false;
    }
    bool Number(JsonValue& value) {
        Skip();
        const char* begin = source_.c_str() + at_;
        char* end = nullptr;
        double number = std::strtod(begin, &end);
        if (end == begin) return false;
        at_ += static_cast<size_t>(end - begin);
        value = JsonValue::Number(number);
        return true;
    }
    bool Object(JsonValue& value) {
        if (!Take('{')) return false;
        value = JsonValue::Object(); Skip();
        if (Take('}')) return true;
        while (at_ < source_.size()) {
            std::string key; if (!String(key) || !Take(':')) return false;
            JsonValue item; if (!Value(item)) return false;
            value.object[key] = std::move(item);
            Skip(); if (Take('}')) return true; if (!Take(',')) return false;
        }
        return false;
    }
    bool Array(JsonValue& value) {
        if (!Take('[')) return false;
        value = JsonValue::Array(); Skip();
        if (Take(']')) return true;
        while (at_ < source_.size()) {
            JsonValue item; if (!Value(item)) return false;
            value.array.push_back(std::move(item));
            Skip(); if (Take(']')) return true; if (!Take(',')) return false;
        }
        return false;
    }
    std::string source_;
    size_t at_ = 0;
};

std::string Quote(const std::string& value) {
    std::ostringstream out; out << '"';
    for (unsigned char c : value) {
        switch (c) {
        case '"': out << "\\\""; break;
        case '\\': out << "\\\\"; break;
        case '\n': out << "\\n"; break;
        case '\r': out << "\\r"; break;
        case '\t': out << "\\t"; break;
        default: if (c < 0x20) out << "\\u" << std::hex << std::setw(4) << std::setfill('0') << static_cast<int>(c) << std::dec; else out << c;
        }
    }
    out << '"'; return out.str();
}
std::string Dump(const JsonValue& value, int depth = 0) {
    const std::string pad(static_cast<size_t>(depth) * 2, ' ');
    const std::string childPad(static_cast<size_t>(depth + 1) * 2, ' ');
    std::ostringstream out;
    switch (value.kind) {
    case JsonValue::Kind::Null: return "null";
    case JsonValue::Kind::Bool: return value.boolean ? "true" : "false";
    case JsonValue::Kind::Number: { out << std::setprecision(15) << value.number; return out.str(); }
    case JsonValue::Kind::String: return Quote(value.string);
    case JsonValue::Kind::Array:
        out << '[';
        for (size_t i = 0; i < value.array.size(); ++i) { if (i) out << ','; out << '\n' << childPad << Dump(value.array[i], depth + 1); }
        if (!value.array.empty()) out << '\n' << pad;
        out << ']';
        return out.str();
    case JsonValue::Kind::Object:
        out << '{'; size_t i = 0;
        for (const auto& [key, item] : value.object) { if (i++) out << ','; out << '\n' << childPad << Quote(key) << ": " << Dump(item, depth + 1); }
        if (!value.object.empty()) out << '\n' << pad;
        out << '}';
        return out.str();
    }
    return "null";
}

const JsonValue* Get(const JsonValue& value, const char* key) {
    if (value.kind != JsonValue::Kind::Object) return nullptr;
    auto it = value.object.find(key); return it == value.object.end() ? nullptr : &it->second;
}
std::string Str(const JsonValue* value, const std::string& fallback = {}) { return value && value->kind == JsonValue::Kind::String ? value->string : fallback; }
double Num(const JsonValue* value, double fallback = 0) { return value && value->kind == JsonValue::Kind::Number ? value->number : fallback; }
bool Bool(const JsonValue* value, bool fallback = false) { return value && value->kind == JsonValue::Kind::Bool ? value->boolean : fallback; }

JsonValue DamageToJson(const DamageSource& source) {
    JsonValue out = JsonValue::Object();
    out.object["id"] = JsonValue::String(source.id); out.object["name"] = JsonValue::String(ToUtf8(source.name));
    out.object["type"] = JsonValue::String(ToUtf8(source.type)); out.object["element"] = JsonValue::String(source.element);
    out.object["reaction"] = JsonValue::String(source.reaction); out.object["multiplier"] = JsonValue::Number(source.multiplier);
    out.object["hits"] = JsonValue::Number(source.hits); out.object["enabled"] = JsonValue::Bool(source.enabled);
    out.object["critical"] = JsonValue::Bool(source.critical); out.object["startTime"] = JsonValue::Number(source.startTime); out.object["duration"] = JsonValue::Number(source.duration);
    return out;
}
DamageSource DamageFromJson(const JsonValue& value) {
    DamageSource d; d.id = Str(Get(value,"id"), NewId()); d.name = FromUtf8(Str(Get(value,"name"), "伤害来源")); d.type = FromUtf8(Str(Get(value,"type"), "元素战技"));
    d.element = Str(Get(value,"element"), "pyro"); d.reaction = Str(Get(value,"reaction")); d.multiplier = Num(Get(value,"multiplier"), 100); d.hits = static_cast<int>(Num(Get(value,"hits"), 1));
    d.enabled = Bool(Get(value,"enabled"), true); d.critical = Bool(Get(value,"critical"), true); d.startTime = Num(Get(value,"startTime")); d.duration = Num(Get(value,"duration")); return d;
}
JsonValue CharacterToJson(const Character& character) {
    JsonValue out = JsonValue::Object();
    out.object["id"] = JsonValue::String(character.id); out.object["name"] = JsonValue::String(ToUtf8(character.name)); out.object["element"] = JsonValue::String(character.element);
    out.object["level"] = JsonValue::Number(character.level); out.object["baseAtk"] = JsonValue::Number(character.baseAtk); out.object["baseDef"] = JsonValue::Number(character.baseDef); out.object["baseHp"] = JsonValue::Number(character.baseHp); out.object["weaponAtk"] = JsonValue::Number(character.weaponAtk);
    out.object["atkPct"] = JsonValue::Number(character.atkPct); out.object["atkFlat"] = JsonValue::Number(character.atkFlat); out.object["defPct"] = JsonValue::Number(character.defPct); out.object["defFlat"] = JsonValue::Number(character.defFlat);
    out.object["hpPct"] = JsonValue::Number(character.hpPct); out.object["hpFlat"] = JsonValue::Number(character.hpFlat); out.object["em"] = JsonValue::Number(character.em); out.object["critRate"] = JsonValue::Number(character.critRate); out.object["critDmg"] = JsonValue::Number(character.critDmg); out.object["energyRecharge"] = JsonValue::Number(character.energyRecharge); out.object["enabled"] = JsonValue::Bool(character.enabled);
    JsonValue bonus = JsonValue::Object(); for (const auto& [key, val] : character.damageBonus) bonus.object[key] = JsonValue::Number(val); out.object["damageBonus"] = std::move(bonus);
    JsonValue sources = JsonValue::Array(); for (const auto& source : character.damageSources) sources.array.push_back(DamageToJson(source)); out.object["damageSources"] = std::move(sources); return out;
}
Character CharacterFromJson(const JsonValue& value) {
    Character c; c.id = Str(Get(value,"id"), NewId()); c.name = FromUtf8(Str(Get(value,"name"), "新角色")); c.element = Str(Get(value,"element"), "pyro"); c.level = static_cast<int>(Num(Get(value,"level"),90));
    c.baseAtk = Num(Get(value,"baseAtk")); c.baseDef = Num(Get(value,"baseDef")); c.baseHp = Num(Get(value,"baseHp")); c.weaponAtk = Num(Get(value,"weaponAtk")); c.atkPct = Num(Get(value,"atkPct")); c.atkFlat = Num(Get(value,"atkFlat")); c.defPct = Num(Get(value,"defPct")); c.defFlat = Num(Get(value,"defFlat")); c.hpPct = Num(Get(value,"hpPct")); c.hpFlat = Num(Get(value,"hpFlat")); c.em = Num(Get(value,"em")); c.critRate = Num(Get(value,"critRate"),5); c.critDmg = Num(Get(value,"critDmg"),50); c.energyRecharge = Num(Get(value,"energyRecharge"),100); c.enabled = Bool(Get(value,"enabled"),true);
    if (const auto* bonus = Get(value,"damageBonus"); bonus && bonus->kind == JsonValue::Kind::Object) for (const auto& [key,val] : bonus->object) c.damageBonus[key] = Num(&val);
    if (const auto* sources = Get(value,"damageSources"); sources && sources->kind == JsonValue::Kind::Array) for (const auto& item : sources->array) c.damageSources.push_back(DamageFromJson(item));
    if (c.damageSources.empty()) { DamageSource source; source.id = NewId(); source.name = L"元素战技"; source.type = L"元素战技"; source.element = c.element; source.multiplier = 100; c.damageSources.push_back(source); }
    return c;
}

JsonValue ConfigToJson(const Config& config) {
    JsonValue out = JsonValue::Object(); out.object["schema"] = JsonValue::String(config.schema); out.object["name"] = JsonValue::String(ToUtf8(config.name)); out.object["enemyLevel"] = JsonValue::Number(config.enemyLevel); out.object["timelineEnabled"] = JsonValue::Bool(config.timelineEnabled); out.object["damageShareEnabled"] = JsonValue::Bool(config.damageShareEnabled); out.object["rotationDuration"] = JsonValue::Number(config.rotationDuration);
    JsonValue resistance = JsonValue::Object(); for (const auto& [key,val] : config.enemyResistance) resistance.object[key] = JsonValue::Number(val); out.object["enemyResistance"] = std::move(resistance);
    JsonValue chars = JsonValue::Array(); for (const auto& c : config.characters) chars.array.push_back(CharacterToJson(c)); out.object["characters"] = std::move(chars);
    JsonValue baselines = JsonValue::Array(); for (const auto& b : config.baselines) { JsonValue v = JsonValue::Object(); v.object["id"] = JsonValue::String(b.id); v.object["name"] = JsonValue::String(ToUtf8(b.name)); v.object["total"] = JsonValue::Number(b.total); baselines.array.push_back(std::move(v)); } out.object["baselines"] = std::move(baselines);
    JsonValue history = JsonValue::Array(); for (const auto& item : config.history) history.array.push_back(JsonValue::String(ToUtf8(item))); out.object["history"] = std::move(history); return out;
}
Config ConfigFromJson(const JsonValue& value) {
    Config c; c.schema = Str(Get(value,"schema"), "gidmg-native-1"); c.name = FromUtf8(Str(Get(value,"name"), "未命名配置")); c.enemyLevel = static_cast<int>(Num(Get(value,"enemyLevel"),93)); c.timelineEnabled = Bool(Get(value,"timelineEnabled"),true); c.damageShareEnabled = Bool(Get(value,"damageShareEnabled"),true); c.rotationDuration = Num(Get(value,"rotationDuration"),20);
    if (const auto* res = Get(value,"enemyResistance"); res && res->kind == JsonValue::Kind::Object) for (const auto& [key,val] : res->object) c.enemyResistance[key] = Num(&val);
    for (const auto& e : {"pyro","hydro","electro","cryo","dendro","anemo","geo","physical"}) if (!c.enemyResistance.count(e)) c.enemyResistance[e] = 10;
    if (const auto* chars = Get(value,"characters"); chars && chars->kind == JsonValue::Kind::Array) for (const auto& item : chars->array) c.characters.push_back(CharacterFromJson(item));
    if (const auto* base = Get(value,"baselines"); base && base->kind == JsonValue::Kind::Array) for (const auto& item : base->array) { Baseline b; b.id = Str(Get(item,"id"), NewId()); b.name = FromUtf8(Str(Get(item,"name"), "基准")); b.total = Num(Get(item,"total")); c.baselines.push_back(b); }
    if (const auto* history = Get(value,"history"); history && history->kind == JsonValue::Kind::Array) for (const auto& item : history->array) c.history.push_back(FromUtf8(Str(&item)));
    return c;
}

} // namespace

std::string ToUtf8(const std::wstring& value) {
    std::string out;
    for (wchar_t wc : value) {
        uint32_t c = static_cast<uint32_t>(wc);
        if (c <= 0x7f) out.push_back(static_cast<char>(c));
        else if (c <= 0x7ff) { out.push_back(static_cast<char>(0xc0 | (c >> 6))); out.push_back(static_cast<char>(0x80 | (c & 0x3f))); }
        else if (c <= 0xffff) { out.push_back(static_cast<char>(0xe0 | (c >> 12))); out.push_back(static_cast<char>(0x80 | ((c >> 6) & 0x3f))); out.push_back(static_cast<char>(0x80 | (c & 0x3f))); }
        else { out.push_back(static_cast<char>(0xf0 | (c >> 18))); out.push_back(static_cast<char>(0x80 | ((c >> 12) & 0x3f))); out.push_back(static_cast<char>(0x80 | ((c >> 6) & 0x3f))); out.push_back(static_cast<char>(0x80 | (c & 0x3f))); }
    }
    return out;
}
std::wstring FromUtf8(const std::string& value) {
    std::wstring out; size_t i = 0;
    while (i < value.size()) { unsigned char c = static_cast<unsigned char>(value[i++]); uint32_t cp = 0; int more = 0;
        if (c < 0x80) cp = c; else if ((c & 0xe0) == 0xc0) { cp = c & 0x1f; more = 1; } else if ((c & 0xf0) == 0xe0) { cp = c & 0x0f; more = 2; } else { cp = c & 0x07; more = 3; }
        for (int n=0; n<more && i<value.size(); ++n) cp = (cp << 6) | (static_cast<unsigned char>(value[i++]) & 0x3f);
#if WCHAR_MAX <= 0xffff
        if (cp > 0xffff) { cp -= 0x10000; out.push_back(static_cast<wchar_t>(0xd800 + (cp >> 10))); out.push_back(static_cast<wchar_t>(0xdc00 + (cp & 0x3ff))); } else
#endif
        out.push_back(static_cast<wchar_t>(cp));
    }
    return out;
}
std::string NewId() {
    static std::mt19937 generator(static_cast<unsigned>(std::chrono::high_resolution_clock::now().time_since_epoch().count()));
    std::uniform_int_distribution<unsigned> distribution(0, 0xffffff);
    std::ostringstream out; out << std::hex << distribution(generator); return out.str();
}

Character MakePreset(const std::string& preset) {
    Character c; c.id = NewId(); c.level = 90; c.critRate = 72; c.critDmg = 210; c.damageBonus["pyro"] = 61.6;
    DamageSource source; source.id = NewId(); source.type = L"元素战技"; source.hits = 1; source.enabled = true; source.critical = true;
    if (preset == "yelan") { c.name=L"夜兰"; c.element="hydro"; c.baseHp=14450; c.baseAtk=244; c.baseDef=548; c.weaponAtk=510; c.hpPct=46.6; c.critRate=65; c.critDmg=180; c.damageBonus["hydro"]=61.6; source.name=L"元素战技·萦络纵命索"; source.type=L"元素战技"; source.element="hydro"; source.multiplier=300; source.reaction="vape"; }
    else if (preset == "raiden") { c.name=L"雷电将军"; c.element="electro"; c.baseHp=12907; c.baseAtk=337; c.baseDef=789; c.weaponAtk=608; c.atkPct=46.6; c.critRate=60; c.critDmg=160; c.damageBonus["electro"]=46.6; source.name=L"元素爆发·梦想真说"; source.type=L"元素爆发"; source.element="electro"; source.multiplier=721; source.reaction="aggravate"; }
    else if (preset == "nahida") { c.name=L"纳西妲"; c.element="dendro"; c.baseHp=10360; c.baseAtk=299; c.baseDef=630; c.weaponAtk=510; c.em=800; c.critRate=55; c.critDmg=120; c.damageBonus["dendro"]=46.6; source.name=L"所闻遍计"; source.type=L"元素战技"; source.element="dendro"; source.multiplier=185; source.reaction="spread"; }
    else if (preset == "furina") { c.name=L"芙宁娜"; c.element="hydro"; c.baseHp=15307; c.baseAtk=243; c.baseDef=696; c.weaponAtk=542; c.hpPct=46.6; c.critRate=60; c.critDmg=180; c.damageBonus["hydro"]=46.6; source.name=L"元素战技·孤心沙龙"; source.type=L"元素战技"; source.element="hydro"; source.multiplier=250; source.reaction=""; }
    else if (preset == "bennett") { c.name=L"班尼特"; c.element="pyro"; c.baseHp=12397; c.baseAtk=191; c.baseDef=771; c.weaponAtk=510; c.atkPct=46.6; c.critRate=55; c.critDmg=110; c.damageBonus["pyro"]=46.6; source.name=L"元素爆发·美妙旅程"; source.type=L"元素爆发"; source.element="pyro"; source.multiplier=300; }
    else { c.name=L"胡桃"; c.element="pyro"; c.baseHp=15552; c.baseAtk=106; c.baseDef=876; c.weaponAtk=510; c.hpPct=116.3; c.em=210; c.critRate=72; c.critDmg=210; c.damageBonus["pyro"]=61.6; source.name=L"重击·蝶引来生"; source.type=L"重击"; source.element="pyro"; source.multiplier=243; source.reaction="vape"; source.startTime=2; source.duration=9; }
    c.damageSources.push_back(source); return c;
}
Config MakeDefaultConfig(const std::wstring& name) {
    Config c; c.name = name; for (const auto& element : {"pyro","hydro","electro","cryo","dendro","anemo","geo","physical"}) c.enemyResistance[element] = 10; c.characters.push_back(MakePreset("hutao")); return c;
}

static double LevelCoefficient(int level) {
    const std::pair<int,double> table[] = {{1,17.17},{20,122.15},{40,277.37},{50,388.07},{60,530.78},{70,685.13},{80,1077.44},{90,1446.85},{95,1711.20},{100,2030.10}};
    level = std::clamp(level, 1, 100); for (size_t i=1; i<std::size(table); ++i) if (level <= table[i].first) { const auto [a,b] = table[i-1]; const auto [x,y] = table[i]; return b + (y-b) * (level-a) / static_cast<double>(x-a); } return table[std::size(table)-1].second;
}
static double ResistanceMultiplier(double resistancePercent) { double r = resistancePercent / 100.0; if (r < 0) return 1 - r / 2; if (r <= .75) return 1 - r; return 1 / (4 * r + 1); }
static double DefenseMultiplier(int playerLevel, int enemyLevel) { return (100.0 + playerLevel) / (100.0 + playerLevel + std::max(1, enemyLevel)); }

Calculation Calculate(const Config& config) {
    Calculation result; const double defense = DefenseMultiplier(90, config.enemyLevel); const double rotation = std::max(1.0, config.rotationDuration);
    for (const Character& c : config.characters) {
        if (!c.enabled) continue;
        double attack = (c.baseAtk + c.weaponAtk) * (1 + c.atkPct / 100.0) + c.atkFlat;
        double hp = c.baseHp * (1 + c.hpPct / 100.0) + c.hpFlat;
        const double resistance = config.enemyResistance.count(c.element) ? config.enemyResistance.at(c.element) : 10;
        double characterTotal = 0;
        for (const DamageSource& source : c.damageSources) {
            if (!source.enabled) continue;
            double stat = source.type == L"生命值" ? hp : attack;
            double direct = stat * source.multiplier / 100.0;
            double critFactor = source.critical ? (1 + std::clamp(c.critRate, 0.0, 100.0) / 100.0 * c.critDmg / 100.0) : 1.0;
            double bonus = c.damageBonus.count(source.element) ? c.damageBonus.at(source.element) : 0;
            double directDamage = direct * critFactor * (1 + bonus / 100.0) * defense * ResistanceMultiplier(resistance) * std::max(1, source.hits);
            double reactionDamage = 0;
            if (source.reaction == "vape" || source.reaction == "melt") directDamage *= source.reaction == "melt" ? 2.0 : 1.5;
            else if (source.reaction == "aggravate" || source.reaction == "spread") reactionDamage = LevelCoefficient(c.level) * (source.reaction == "aggravate" ? 1.15 : 1.25) * (1 + 5.78 * c.em / (c.em + 1200.0)) * ResistanceMultiplier(resistance) * std::max(1, source.hits);
            else if (source.reaction == "overloaded" || source.reaction == "hyperbloom" || source.reaction == "burgeon" || source.reaction == "bloom") reactionDamage = LevelCoefficient(c.level) * (source.reaction == "bloom" ? 2.0 : 3.0) * (1 + 16.0 * c.em / (c.em + 2000.0)) * ResistanceMultiplier(resistance) * std::max(1, source.hits);
            double value = std::max(0.0, directDamage + reactionDamage);
            if (config.timelineEnabled && source.duration > 0) value *= std::min(1.0, source.duration / rotation);
            characterTotal += value; result.total += value;
            result.sources.push_back({source.name, c.name, source.element, source.reaction, value, 0});
        }
        result.characterTotals[c.id] = characterTotal;
    }
    result.dps = config.timelineEnabled ? result.total / rotation : 0;
    for (auto& item : result.sources) { const auto it = result.characterTotals.begin(); (void)it; auto character = std::find_if(config.characters.begin(), config.characters.end(), [&](const Character& c){ return c.name == item.character; }); double total = character == config.characters.end() ? 0 : result.characterTotals.at(character->id); item.share = total > 0 ? item.value / result.total : 0; }
    return result;
}

ConfigStore::ConfigStore(std::filesystem::path executableDirectory) : dateDirectory_(std::move(executableDirectory) / "date") { std::error_code error; std::filesystem::create_directories(dateDirectory_, error); }
std::vector<std::filesystem::path> ConfigStore::List() const { std::vector<std::filesystem::path> result; std::error_code error; if (!std::filesystem::exists(dateDirectory_, error)) return result; for (const auto& entry : std::filesystem::directory_iterator(dateDirectory_, error)) if (entry.is_regular_file() && entry.path().extension() == ".json") result.push_back(entry.path()); std::sort(result.begin(), result.end()); return result; }
std::filesystem::path ConfigStore::PathFor(const std::wstring& name) const { std::wstring safe = name.empty() ? L"未命名配置" : name; for (wchar_t& c : safe) if (c == L'\\' || c == L'/' || c == L':' || c == L'*' || c == L'?' || c == L'"' || c == L'<' || c == L'>' || c == L'|') c = L'_'; return dateDirectory_ / (safe + L".json"); }
bool ConfigStore::Save(const Config& config, const std::filesystem::path& path) const { std::error_code error; std::filesystem::create_directories(path.parent_path(), error); std::ofstream file(path, std::ios::binary); if (!file) return false; const std::string data = Dump(ConfigToJson(config)); file.write(data.data(), static_cast<std::streamsize>(data.size())); return file.good(); }
bool ConfigStore::Load(const std::filesystem::path& path, Config& config) const { std::ifstream file(path, std::ios::binary); if (!file) return false; std::string data((std::istreambuf_iterator<char>(file)), {}); JsonValue value; if (!JsonParser(std::move(data)).Parse(value)) return false; config = ConfigFromJson(value); return true; }
bool ConfigStore::Remove(const std::filesystem::path& path) const { std::error_code error; return std::filesystem::remove(path, error); }

} // namespace gidmg
