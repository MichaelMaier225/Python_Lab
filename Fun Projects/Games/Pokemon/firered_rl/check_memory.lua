-- Pokémon FireRed: read-only mGBA memory access test.
-- Run from mGBA: Tools > Scripting > Load script.
-- Does not change game memory or saved games.

if not emu then
    console:error('Load Pokémon FireRed in mGBA before running this script.')
    return
end

local EWRAM = 0x02000000
local IWRAM = 0x03000000

local function check(label, address)
    local ok, value = pcall(function() return emu:read32(address) end)
    if ok then
        console:log(string.format('%s at 0x%08X: 0x%08X', label, address, value))
    else
        console:error(label .. ' read failed: ' .. tostring(value))
    end
end

console:log('=== FireRed memory access test ===')
check('EWRAM', EWRAM)
check('EWRAM + 0x100', EWRAM + 0x100)
check('IWRAM', IWRAM)

if emu.memory then
    console:log('Memory domains:')
    for key, domain in pairs(emu.memory) do
        local ok, base, size = pcall(function()
            return domain:base(), domain:size()
        end)
        if ok then
            console:log(string.format('  %s: base=0x%08X size=%d', tostring(key), base, size))
        end
    end
end

console:log('Test complete. These are raw memory values, not verified player coordinates.')
