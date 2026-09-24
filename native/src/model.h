#pragma once

#include <filesystem>
#include <map>
#include <string>
#include <vector>

namespace gidmg {

struct DamageSource {
    std::string id;
    std::wstring name;
    std::wstring type;
    std::string element;
    std::string reaction;
    double multiplier = 100.0;
    int hits = 1;
    bool enabled = true;
    bool critical = true;
    double startTime = 0.0;
    double duration = 0.0;
};

struct Character {
    std::string id;
    std::wstring name;
    std::string element = "pyro";
    int level = 90;
    double baseAtk = 0.0;
    double baseDef = 0.0;
    double baseHp = 0.0;
    double weaponAtk = 0.0;
    double atkPct = 0.0;
    double atkFlat = 0.0;
    double defPct = 0.0;
    double defFlat = 0.0;
    double hpPct = 0.0;
    double hpFlat = 0.0;
    double em = 0.0;
    double critRate = 5.0;
    double critDmg = 50.0;
    double energyRecharge = 100.0;
    std::map<std::string, double> damageBonus;
    std::vector<DamageSource> damageSources;
    bool enabled = true;
};

struct Baseline {
    std::string id;
    std::wstring name;
    double total = 0.0;
};

struct Config {
    std::string schema = "gidmg-native-1";
    std::wstring name;
    int enemyLevel = 93;
    std::map<std::string, double> enemyResistance;
    bool timelineEnabled = true;
    bool damageShareEnabled = true;
    double rotationDuration = 20.0;
    std::vector<Character> characters;
    std::vector<Baseline> baselines;
    std::vector<std::wstring> history;
};

struct DamageResult {
    std::wstring name;
    std::wstring character;
    std::string element;
    std::string reaction;
    double value = 0.0;
    double share = 0.0;
};

struct Calculation {
    double total = 0.0;
    double dps = 0.0;
    std::vector<DamageResult> sources;
    std::map<std::string, double> characterTotals;
};

std::string ToUtf8(const std::wstring& value);
std::wstring FromUtf8(const std::string& value);
std::string NewId();
Character MakePreset(const std::string& preset);
Config MakeDefaultConfig(const std::wstring& name);
Calculation Calculate(const Config& config);

class ConfigStore {
public:
    explicit ConfigStore(std::filesystem::path executableDirectory);
    const std::filesystem::path& dateDirectory() const { return dateDirectory_; }
    std::vector<std::filesystem::path> List() const;
    bool Save(const Config& config, const std::filesystem::path& path) const;
    bool Load(const std::filesystem::path& path, Config& config) const;
    bool Remove(const std::filesystem::path& path) const;
    std::filesystem::path PathFor(const std::wstring& name) const;

private:
    std::filesystem::path dateDirectory_;
};

} // namespace gidmg
