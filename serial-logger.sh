#!/bin/bash

# --- CONFIGURATION ---
PORT="/dev/ttyUSB2"
BAUD="115200"
LOG_DIR="./logs"
BASE_NAME="serial_log"
LINE_LIMIT=32000
# ---------------------

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Open the port once (RDWR so DTR stays asserted) and configure it on that
# fd. Closing between stty and cat can drop DTR and reset the target.
exec 3<>"$PORT"
stty -F "$PORT" "$BAUD" raw -echo -echoe -echok clocal min 1 time 0

# Find the highest existing 4-digit suffix in the log directory
max_num=0
for file in "$LOG_DIR"/"$BASE_NAME"_[0-9][0-9][0-9][0-9].log; do
    # Check if any files actually matched the glob pattern
    [ -e "$file" ] || break

    # Extract the 4-digit number from the filename
    filename=$(basename "$file")
    num=$(echo "$filename" | grep -o '[0-9]\{4\}' | sed 's/^0*//')

    # Handle the case where 0000 becomes empty string after stripping zeros
    [ -z "$num" ] && num=0

    if [ "$num" -gt "$max_num" ]; then
        max_num=$num
    fi
done

# If logs already exist, increment the counter. Otherwise, start at 1.
if ls "$LOG_DIR"/"$BASE_NAME"_[0-9][0-9][0-9][0-9].log >/dev/null 2>&1; then
    next_num=$((max_num + 1))
else
    next_num=1
fi

# Format the counter as a zero-padded, 4-digit string (e.g., 0001)
printf -v SUFFIX "%04d" $next_num
LOG_FILE="$LOG_DIR/${BASE_NAME}_${SUFFIX}.log"

echo "Listening on $PORT ($BAUD baud)..."
echo "Logging $LINE_LIMIT lines to: $LOG_FILE"

# Do not use `cat "$PORT" | head -n N | tee`. GNU cat splice()s the tty into
# the pipe; a 0-byte splice (empty 4096-byte n_tty buffer between bursts)
# is treated as EOF, so the log stops at exactly 4096 bytes. Read the port
# with blocking line reads instead (VMIN=1).
count=0
while IFS= read -r line || [ -n "$line" ]; do
    printf '%s\n' "$line"
    printf '%s\n' "$line" >&4
    count=$((count + 1))
    [ "$count" -ge "$LINE_LIMIT" ] && break
done <&3 4>"$LOG_FILE"

exec 3>&-

echo -e "\nFinished! Saved $count lines to $LOG_FILE"
