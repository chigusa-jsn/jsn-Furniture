package com.chigusa.jsnfurniture.block;

import com.chigusa.jsnfurniture.JsnFurniture;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

/** 動く家具（ファン・時計・ロッキングチェア・洗濯機・ブランコ）。中身はなく、動きは AnimRenderer が描く */
public class AnimBlockEntity extends BlockEntity {
    /** 回転の角度（画面側で、つけたり消したりしてもなめらかに止まるように） */
    public float spin;
    public float spinSpeed;
    public long lastFrame = -1;

    public AnimBlockEntity(BlockPos pos, BlockState state) {
        super(JsnFurniture.ANIM_BE.get(), pos, state);
    }
}
