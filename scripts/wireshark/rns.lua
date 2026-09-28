-- SPDX-License-Identifier: 0BSD
-- Wireshark/tshark dissector for the Reticulum wire format.
--
-- Usage:
--   tshark -X lua_script:rns.lua -r capture.pcap -Y 'rns.packet_type == 1'
--   wireshark -X lua_script:rns.lua
-- Or copy into the personal plugins dir to load at startup:
--   ~/.local/lib/wireshark/plugins/rns.lua
--
-- Decodes:
--   * Raw RNS packets in UDP datagrams (heuristic, any port).
--   * HDLC-framed RNS packets on TCP streams via Decode As -> rnshdlc.
--     The shared Reticulum instance port 37428 is pre-registered.
--
-- Filter examples:
--   rns                       any decoded RNS packet
--   rns.packet_type == 1      announces only
--   rns.packet_type == 2      link requests (the RRC retry traffic)
--   rns.packet_type == 3      proofs
--   rns.hops > 0              packets that travelled at least one hop
--   rns.context == 0xfb       link identify packets
--
-- Packet layout (RNS.Packet):
--   byte 0 flags: [7:6] header_type, [5] context_flag, [4] transport_type,
--                 [3:2] destination_type, [1:0] packet_type
--   byte 1 hops
--   HEADER_2: 16 byte transport_id then 16 byte destination_hash
--   HEADER_1: 16 byte destination_hash (or link id when dest type is LINK)
--   1 byte context, then ciphertext/data

local p_rns = Proto("rns", "Reticulum Packet")

local header_type_names = {[0] = "HEADER_1", [1] = "HEADER_2"}
local transport_type_names = {
    [0] = "BROADCAST", [1] = "TRANSPORT", [2] = "RELAY", [3] = "TUNNEL",
}
local destination_type_names = {
    [0] = "SINGLE", [1] = "GROUP", [2] = "PLAIN", [3] = "LINK",
}
local packet_type_names = {
    [0] = "DATA", [1] = "ANNOUNCE", [2] = "LINKREQUEST", [3] = "PROOF",
}
local context_names = {
    [0x00] = "NONE",
    [0x01] = "RESOURCE", [0x02] = "RESOURCE_ADV", [0x03] = "RESOURCE_REQ",
    [0x04] = "RESOURCE_HMU", [0x05] = "RESOURCE_PRF",
    [0x06] = "RESOURCE_ICL", [0x07] = "RESOURCE_RCL",
    [0x08] = "CACHE_REQUEST", [0x09] = "REQUEST", [0x0A] = "RESPONSE",
    [0x0B] = "PATH_RESPONSE", [0x0C] = "COMMAND", [0x0D] = "COMMAND_STATUS",
    [0x0E] = "CHANNEL",
    [0xFA] = "KEEPALIVE", [0xFB] = "LINKIDENTIFY", [0xFC] = "LINKCLOSE",
    [0xFD] = "LINKPROOF", [0xFE] = "LRRTT", [0xFF] = "LRPROOF",
}

local f = p_rns.fields
f.flags = ProtoField.uint8("rns.flags", "Flags", base.HEX)
f.header_type = ProtoField.uint8("rns.header_type", "Header Type", base.DEC, header_type_names, 0xC0)
f.context_flag = ProtoField.uint8("rns.context_flag", "Context Flag", base.DEC, {[0] = "UNSET", [1] = "SET"}, 0x20)
f.transport_type = ProtoField.uint8("rns.transport_type", "Transport Type", base.DEC, transport_type_names, 0x10)
f.destination_type = ProtoField.uint8("rns.destination_type", "Destination Type", base.DEC, destination_type_names, 0x0C)
f.packet_type = ProtoField.uint8("rns.packet_type", "Packet Type", base.DEC, packet_type_names, 0x03)
f.hops = ProtoField.uint8("rns.hops", "Hops", base.DEC)
f.transport_id = ProtoField.bytes("rns.transport_id", "Transport ID")
f.destination = ProtoField.bytes("rns.destination", "Destination Hash")
f.context = ProtoField.uint8("rns.context", "Context", base.HEX, context_names)
f.data = ProtoField.bytes("rns.data", "Data")

local function name_or(map, v)
    return map[v] or string.format("0x%02x", v)
end

-- Dissect one raw RNS packet tvb. Returns true when parsed.
local function dissect_packet(tvb, pinfo, tree)
    local len = tvb:len()
    if len < 19 then return false end

    local flags = tvb(0, 1):uint()
    local header_type = bit.rshift(bit.band(flags, 0xC0), 6)
    local transport_type = bit.rshift(bit.band(flags, 0x10), 4)
    local destination_type = bit.rshift(bit.band(flags, 0x0C), 2)
    local packet_type = bit.band(flags, 0x03)
    local hops = tvb(1, 1):uint()
    if hops >= 128 or header_type > 1 then return false end
    if header_type == 1 and len < 35 then return false end

    local offset = 2
    local subtree = tree:add(p_rns, tvb(), "Reticulum Packet")
    subtree:add(f.flags, tvb(0, 1))
    subtree:add(f.header_type, tvb(0, 1))
    subtree:add(f.context_flag, tvb(0, 1))
    subtree:add(f.transport_type, tvb(0, 1))
    subtree:add(f.destination_type, tvb(0, 1))
    subtree:add(f.packet_type, tvb(0, 1))
    subtree:add(f.hops, tvb(1, 1))

    if header_type == 1 then
        subtree:add(f.transport_id, tvb(offset, 16))
        offset = offset + 16
    end
    subtree:add(f.destination, tvb(offset, 16))
    offset = offset + 16
    local context = tvb(offset, 1):uint()
    subtree:add(f.context, tvb(offset, 1))
    offset = offset + 1
    if offset < len then
        subtree:add(f.data, tvb(offset))
    end

    pinfo.cols.protocol = "RNS"
    local info = string.format(
        "%s dst=%s ctx=%s hops=%d len=%d",
        name_or(packet_type_names, packet_type),
        tostring(tvb(offset - 17, 16):bytes()):sub(1, 8),
        name_or(context_names, context),
        hops,
        len
    )
    if destination_type == 3 then
        info = info .. " (link data)"
    end
    if pinfo.cols.info then
        pinfo.cols.info:set(tostring(info))
    else
        pinfo.cols.info = info
    end
    return true
end

function p_rns.dissector(tvb, pinfo, tree)
    return dissect_packet(tvb, pinfo, tree)
end

-- Heuristic on UDP: a datagram is a raw RNS packet when the flags byte and
-- hop count are sane and the size matches the header it claims.
local function heur_udp(tvb, pinfo, tree)
    local len = tvb:len()
    if len < 19 then return false end
    local flags = tvb(0, 1):uint()
    local header_type = bit.rshift(bit.band(flags, 0xC0), 6)
    local hops = tvb(1, 1):uint()
    if header_type > 1 or hops >= 128 then return false end
    if header_type == 1 and len < 35 then return false end
    return dissect_packet(tvb, pinfo, tree)
end
p_rns:register_heuristic("udp", heur_udp)

-- HDLC framing over TCP: FLAG(0x7E) + escaped payload + FLAG.
-- Registered for the shared-instance default port; use Decode As for others.
local p_hdlc = Proto("rnshdlc", "Reticulum HDLC over TCP")

local f_frame = ProtoField.bytes("rnshdlc.frame", "HDLC Frame")
p_hdlc.fields = { f_frame }

local HDLC_FLAG = 0x7E
local HDLC_ESC = 0x7D
local HDLC_ESC_MASK = 0x20

local function find_flag(tvb, from)
    local len = tvb:len()
    for i = from, len - 1 do
        if tvb(i, 1):uint() == HDLC_FLAG then return i end
    end
    return nil
end

local function unescape(frame_tvb)
    local n = frame_tvb:len()
    local parts = {}
    local i = 0
    while i < n do
        local b = frame_tvb(i, 1):uint()
        if b == HDLC_ESC and i + 1 < n then
            parts[#parts + 1] = string.format(
                "%02x", bit.bxor(frame_tvb(i + 1, 1):uint(), HDLC_ESC_MASK)
            )
            i = i + 2
        else
            parts[#parts + 1] = string.format("%02x", b)
            i = i + 1
        end
    end
    return table.concat(parts)
end

function p_hdlc.dissector(tvb, pinfo, tree)
    local len = tvb:len()
    local offset = 0
    local found_any = false

    while true do
        local flag_start = find_flag(tvb, offset)
        if flag_start == nil then
            if not found_any then
                -- No frame boundary at all; probably not our protocol.
                return
            end
            if len - offset > 0 then
                pinfo.desegment_offset = offset
                pinfo.desegment_len = DESEGMENT_ONE_MORE_SEGMENT
            end
            return
        end
        local flag_end = find_flag(tvb, flag_start + 1)
        if flag_end == nil then
            -- Frame runs into the next segment; hold it for reassembly.
            pinfo.desegment_offset = flag_start
            pinfo.desegment_len = DESEGMENT_ONE_MORE_SEGMENT
            return
        end

        local frame_len = flag_end - flag_start - 1
        if frame_len > 0 then
            local raw = unescape(tvb(flag_start + 1, frame_len))
            local ptvb = ByteArray.new(raw):tvb("RNS Packet")
            local subtree = tree:add(p_hdlc, tvb(flag_start, flag_end - flag_start + 1), "RNS HDLC Frame")
            subtree:add(f_frame, tvb(flag_start + 1, frame_len))
            local ok = dissect_packet(ptvb, pinfo, subtree)
            found_any = found_any or ok
        end
        offset = flag_end + 1
        if offset >= len then return end
    end
end

local tcp_table = DissectorTable.get("tcp.port")
tcp_table:add(37428, p_hdlc)
