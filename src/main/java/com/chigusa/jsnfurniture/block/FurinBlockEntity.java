package com.chigusa.jsnfurniture.block;

import com.chigusa.jsnfurniture.JsnFurniture;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

/** 風鈴：ゆれ方を覚えておくだけ（絵は FurinRenderer） */
public class FurinBlockEntity extends BlockEntity {
    /** 最後に鳴った時刻と強さ（画面側だけで使う） */
    public long ringAt = -1000;
    public float ringPower;
    /** 風鈴ごとに、ゆれのタイミングを少しずらす */
    public final float phase;

    public FurinBlockEntity(BlockPos pos, BlockState state) {
        super(JsnFurniture.FURIN_BE.get(), pos, state);
        phase = (pos.asLong() * 31 % 1000) / 1000f * 6.28f;
    }

    public void ring(long time, float power) {
        ringAt = time;
        ringPower = power;
    }

    @Override
    public boolean triggerEvent(int id, int param) {
        if (id == 1 && level != null && level.isClientSide) {
            ring(level.getGameTime(), 1.0f);
            return true;
        }
        return super.triggerEvent(id, param);
    }
}
