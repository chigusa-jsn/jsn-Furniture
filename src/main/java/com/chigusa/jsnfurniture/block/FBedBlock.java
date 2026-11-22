package com.chigusa.jsnfurniture.block;

import net.minecraft.core.BlockPos;
import net.minecraft.world.item.DyeColor;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.BedBlock;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.RenderShape;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.VoxelShape;
import org.jetbrains.annotations.Nullable;

/** 木の枠のベッド・布団。寝る・リスポーンはバニラのベッドと同じ（見た目だけモデルにする） */
public class FBedBlock extends BedBlock {
    private static final VoxelShape FUTON = Block.box(0, 0, 0, 16, 4, 16);
    private final boolean futon;

    public FBedBlock(boolean futon, Properties props) {
        super(DyeColor.WHITE, props);
        this.futon = futon;
    }

    @Override
    protected RenderShape getRenderShape(BlockState state) {
        return RenderShape.MODEL;
    }

    @Nullable
    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return null;
    }

    @Override
    protected VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext ctx) {
        return futon ? FUTON : super.getShape(state, level, pos, ctx);
    }
}
