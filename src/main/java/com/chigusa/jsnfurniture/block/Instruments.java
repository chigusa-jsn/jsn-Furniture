package com.chigusa.jsnfurniture.block;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.BlockHitResult;

/** 楽器とダーツ */
public final class Instruments {
    /** ギター：ペンタトニック（どれを鳴らしてもきれい） */
    private static final int[] PENTA = {0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24};

    public static void play(ServerLevel level, BlockPos pos, Direction facing, String kind, BlockHitResult hit, Player player) {
        // 鍵盤の左から右へ：家具のモデルの x を、向きに合わせて取り出す
        double lx = switch (facing) {
            case SOUTH -> 1 - (hit.getLocation().x - pos.getX());
            case EAST -> hit.getLocation().z - pos.getZ();
            case WEST -> 1 - (hit.getLocation().z - pos.getZ());
            default -> hit.getLocation().x - pos.getX();
        };
        lx = Math.max(0, Math.min(0.999, lx));
        int note;
        SoundEvent sound;
        switch (kind) {
            case "piano" -> {
                note = (int) Math.round((1 - lx) * 24);
                sound = SoundEvents.NOTE_BLOCK_HARP.value();
            }
            case "xylophone" -> {
                note = (int) Math.round((1 - lx) * 24);
                sound = SoundEvents.NOTE_BLOCK_XYLOPHONE.value();
            }
            case "guitar" -> {
                note = PENTA[level.random.nextInt(PENTA.length)];
                sound = SoundEvents.NOTE_BLOCK_GUITAR.value();
            }
            case "taiko" -> {
                note = player.isShiftKeyDown() ? 18 : 6;
                sound = player.isShiftKeyDown() ? SoundEvents.NOTE_BLOCK_HAT.value() : SoundEvents.NOTE_BLOCK_BASEDRUM.value();
            }
            default -> {
                return;
            }
        }
        float pitch = (float) Math.pow(2.0, (note - 12) / 12.0);
        level.playSound(null, pos, sound, SoundSource.RECORDS, kind.equals("taiko") ? 1.5f : 1.0f, pitch);
        level.sendParticles(ParticleTypes.NOTE, pos.getX() + 0.5, pos.getY() + 1.1, pos.getZ() + 0.5, 0, note / 24.0, 0, 0, 1);
    }

    public static void darts(ServerLevel level, BlockPos pos, Player player) {
        int r = level.random.nextInt(100);
        String msg;
        if (r < 5) msg = "🎯 ブル！ 50点！";
        else if (r < 12) msg = "トリプル " + (1 + level.random.nextInt(20)) * 3 + "点！";
        else if (r < 20) msg = "ダブル " + (1 + level.random.nextInt(20)) * 2 + "点";
        else if (r < 92) msg = (1 + level.random.nextInt(20)) + "点";
        else msg = "はずれ…";
        level.playSound(null, pos, SoundEvents.ARROW_HIT, SoundSource.BLOCKS, 1f, 1.2f);
        player.displayClientMessage(Component.literal(msg), true);
    }

    private Instruments() {}
}
