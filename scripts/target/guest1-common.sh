# Shared helpers for the guest1 tools. Install beside the executable scripts.
# The lock coordinates these tools only; do not run other domain-management
# commands concurrently. xl does not offer an atomic UUID-checked pause API.

guest1_error() {
    printf '%s\n' "guest1: $*" >&2
}

guest1_require_root() {
    [ "$(id -u)" = 0 ] || {
        guest1_error 'run this tool in the Dom0 root shell'
        return 1
    }
    command -v xl >/dev/null 2>&1 || {
        guest1_error 'xl is unavailable'
        return 1
    }
}

# Output: ID UUID state. Return 3 only when a successful listing has no guest1.
# xl list -v columns are Name ID Mem VCPUs State Time(s) UUID ... (Xen 4.x).
guest1_snapshot() {
    guest1_listing=$(LC_ALL=C xl list -v) || {
        guest1_error 'cannot query the Xen toolstack'
        return 1
    }
    printf '%s\n' "$guest1_listing" | awk '
        NR == 1 {
            if ($1 != "Name" || $2 != "ID" || $5 != "State" || $7 != "UUID")
                bad = 1
            next
        }
        $1 == "guest1" {
            count++
            id = $2
            state = $5
            uuid = $7
            n = split(uuid, parts, "-")
            if (id !~ /^[0-9]+$/ || id + 0 < 1 || id + 0 >= 32752 ||
                state !~ /^[-r][-b][-p][-s][-rscwS?][-d]$/ ||
                n != 5 || length(parts[1]) != 8 || length(parts[2]) != 4 ||
                length(parts[3]) != 4 || length(parts[4]) != 4 ||
                length(parts[5]) != 12 || uuid ~ /[^0-9a-fA-F-]/)
                bad = 1
        }
        END {
            if (NR == 0 || bad || count > 1) exit 2
            if (count == 0) exit 3
            print id, tolower(uuid), state
        }
    '
}

guest1_lock() {
    guest1_lock_dir=${GUEST1_LOCK_DIR:-/run/lock/guest1-tools.lock}
    umask 077
    if ! mkdir "$guest1_lock_dir"; then
        guest1_error "cannot acquire $guest1_lock_dir; another tool may be active"
        return 1
    fi
    guest1_lock_owned=1
}

guest1_unlock() {
    if [ "${guest1_lock_owned:-0}" = 1 ]; then
        rmdir "$guest1_lock_dir" || return 1
        guest1_lock_owned=0
    fi
}
