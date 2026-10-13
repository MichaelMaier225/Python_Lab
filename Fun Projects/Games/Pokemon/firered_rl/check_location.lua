-- Pokemon FireRed: inspect candidate save-block pointers and coordinates.
-- Read-only. Load the game and move around while watching the scripting console.
local candidates = {0x03005008, 0x0300500C}
local last = ''
local frames = 0

local function inspect()
    local lines = {}
    for _, addr in ipairs(candidates) do
        local ptr = emu:read32(addr)
        local valid = ptr >= 0x02000000 and ptr <= 0x0203FFF0
        if valid then
            local x = emu:read16(ptr)
            local y = emu:read16(ptr + 2)
            local group = emu:read8(ptr + 4)
            local map = emu:read8(ptr + 5)
            lines[#lines+1] = string.format('ptr@%08X=%08X  x=%d y=%d  group=%d map=%d', addr, ptr, x, y, group, map)
        else
            lines[#lines+1] = string.format('ptr@%08X=%08X (not an EWRAM pointer)', addr, ptr)
        end
    end
    local result = table.concat(lines, '\n')
    if result ~= last then
        console:log(result)
        last = result
    end
end

console:log('FireRed location probe started. Walk a few steps and watch for changing x/y. Then change rooms.')
inspect()
callbacks:add('frame', function()
    frames = frames + 1
    if frames % 60 == 0 then inspect() end
end)
