#!/bin/bash
# 动物与伙伴补齐 + basic77 音频回滚修复 统一流水线
# 用法: pipeline.sh tts | finish | status
set -u
cd /home/z/my-project/scripts

n_basic() { ls /home/z/my-project/gen_tts/raw/basic_block_world_things-*.wav 2>/dev/null | wc -l; }
n_ani()   { ls /home/z/my-project/gen_tts/raw_animals/animals_and_friends-*.wav 2>/dev/null | wc -l; }
status_line() { echo "STATUS basic=$(n_basic)/308 animals=$(n_ani)/408"; }

case "${1:-status}" in

  tts)
    if [ "$(n_basic)" -lt 308 ] && [ ! -f /home/z/my-project/gen_tts/_basic_repaired.done ]; then
      echo "ROUND basic77 repair..."
      BUDGET_MS=480000 node zai_tts_batch.mjs > /home/z/my-project/gen_tts/_log_fix_t.txt 2>&1
      grep -c "^OK" /home/z/my-project/gen_tts/_log_fix_t.txt || true
    else
      echo "ROUND animals..."
      CONTENT_JSON=/home/z/my-project/scripts/animals102_content.json \
      OUT_RAW=/home/z/my-project/gen_tts/raw_animals \
      BUDGET_MS=480000 node zai_tts_batch.mjs > /home/z/my-project/gen_tts/_log_ani_t.txt 2>&1
      grep -c "^OK" /home/z/my-project/gen_tts/_log_ani_t.txt || true
    fi
    status_line
    if { [ "$(n_basic)" -ge 308 ] || [ -f /home/z/my-project/gen_tts/_basic_repaired.done ]; } && [ "$(n_ani)" -ge 408 ]; then echo "ALL_READY"; fi
    ;;

  finish)
    set -a; . /home/z/my-project/scripts/.deploy_env; set +a
    B=$(n_basic); A=$(n_ani)
    if [ "$A" -lt 408 ] || [ ! -f /home/z/my-project/gen_tts/_basic_repaired.done ]; then status_line; echo "NOT_READY"; exit 0; fi
    if [ ! -f /home/z/my-project/gen_tts/_basic_repaired.done ]; then
      python3 hx_assemble_basic77.py > /home/z/my-project/gen_tts/_log_fix_assemble.txt 2>&1 \
        && touch /home/z/my-project/gen_tts/_basic_repaired.done \
        || { echo ASSEMBLE_BASIC_FAIL; tail -3 /home/z/my-project/gen_tts/_log_fix_assemble.txt; exit 1; }
    fi
    if [ -f /home/z/my-project/gen_tts/_animals_deployed.done ]; then echo "ALREADY_DEPLOYED"; exit 0; fi
    python3 hx_assemble_animals.py > /home/z/my-project/gen_tts/_log_ani_assemble.txt 2>&1 \
      || { echo ASSEMBLE_ANI_FAIL; tail -3 /home/z/my-project/gen_tts/_log_ani_assemble.txt; exit 1; }
    python3 hx_check_mirror.py > /home/z/my-project/gen_tts/_log_check.txt 2>&1 \
      || { echo CHECK_FAIL; tail -3 /home/z/my-project/gen_tts/_log_check.txt; exit 1; }
    python3 vercel_deploy_inline.py > /home/z/my-project/gen_tts/_log_vercel.txt 2>&1 \
      || { echo VERCEL_FAIL; tail -3 /home/z/my-project/gen_tts/_log_vercel.txt; exit 1; }
    python3 github_push_readings_fix.py > /home/z/my-project/gen_tts/_log_gh.txt 2>&1 \
      || { echo GH_FAIL; tail -3 /home/z/my-project/gen_tts/_log_gh.txt; exit 1; }
    DEP=$(grep -o 'dpl_[A-Za-z0-9]*' /home/z/my-project/gen_tts/_log_vercel.txt | tail -1)
    sed -i "s/^DEP_ID = .*/DEP_ID = \"$DEP\"/" hx_verify_remote.py
    python3 hx_verify_remote.py > /home/z/my-project/gen_tts/_log_verify.txt 2>&1
    python3 hx_rebuild_zip.py > /home/z/my-project/gen_tts/_log_zip.txt 2>&1
    touch /home/z/my-project/gen_tts/_animals_deployed.done
    echo "ALL_DONE"
    ;;

  status)
    status_line
    ;;

esac
