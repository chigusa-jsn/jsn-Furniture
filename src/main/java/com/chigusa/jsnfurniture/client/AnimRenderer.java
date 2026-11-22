package com.chigusa.jsnfurniture.client;

import com.chigusa.jsnfurniture.JsnFurniture;
import com.chigusa.jsnfurniture.block.AnimBlockEntity;
import com.chigusa.jsnfurniture.block.FurnitureBlock;
import com.chigusa.jsnfurniture.block.SeatEntity;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.client.renderer.blockentity.BlockEntityRendererProvider;
import net.minecraft.client.resources.model.BakedModel;
import net.minecraft.client.resources.model.ModelResourceLocation;
import net.minecraft.core.Direction;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.neoforged.neoforge.client.model.data.ModelData;

/**
 * 動く家具の、動く部分を描く。
 * fan：回る / clock・grandfather：針が時間で動く（柱時計は振り子も）/ rocker：座るとゆれる
 * washer：回る / swing：座るとブランコがゆれる
 */
public class AnimRenderer implements BlockEntityRenderer<AnimBlockEntity> {
    public AnimRenderer(BlockEntityRendererProvider.Context ctx) {
    }

    public static ModelResourceLocation part(String id, String part) {
        return ModelResourceLocation.standalone(ResourceLocation.fromNamespaceAndPath(JsnFurniture.MODID, "block/" + id + "_" + part));
    }

    @Override
    public void render(AnimBlockEntity be, float partial, PoseStack pose, MultiBufferSource buffers, int light, int overlay) {
        Level level = be.getLevel();
        BlockState st = be.getBlockState();
        if (level == null || !(st.getBlock() instanceof FurnitureBlock fb)) return;
        String id = fb.spec.id();
        double time = level.getGameTime() + partial;
        boolean on = !st.hasProperty(FurnitureBlock.LIT) || st.getValue(FurnitureBlock.LIT);
        pose.pushPose();
        // 向き（モデルは北向きが基準）
        Direction facing = st.getValue(FurnitureBlock.FACING);
        pose.translate(0.5, 0, 0.5);
        pose.mulPose(Axis.YP.rotationDegrees(-switch (facing) {
            case EAST -> 90f;
            case SOUTH -> 180f;
            case WEST -> 270f;
            default -> 0f;
        }));
        pose.translate(-0.5, 0, -0.5);
        switch (fb.spec.anim()) {
            case "fan" -> {
                spinTo(be, time, on ? 18f : 0f);
                draw(pose, buffers, light, overlay, st, part(id, "anim"), 8, 11, 8, Axis.YP, be.spin);
            }
            case "washer" -> {
                spinTo(be, time, on ? 14f : 0f);
                draw(pose, buffers, light, overlay, st, part(id, "anim"), 8, 7, 1.5, Axis.ZP, be.spin);
            }
            case "clock", "grandfather" -> {
                long day = level.getDayTime() % 24000L;
                double hours = (day / 1000.0 + 6) % 24;
                float hourAng = (float) ((hours % 12) / 12.0 * 360.0);
                float minAng = (float) ((hours % 1.0) * 360.0);
                double cy = fb.spec.anim().equals("clock") ? 8 : 26;
                draw(pose, buffers, light, overlay, st, part(id, "hour"), 8, cy, 8, Axis.ZP, hourAng);
                draw(pose, buffers, light, overlay, st, part(id, "min"), 8, cy, 8, Axis.ZP, minAng);
                if (fb.spec.anim().equals("grandfather")) {
                    draw(pose, buffers, light, overlay, st, part(id, "pendulum"), 8, 20, 8, Axis.ZP, (float) Math.sin(time * Math.PI / 20.0) * 14f);
                }
            }
            case "rocker" -> {
                float a = occupied(be) ? (float) Math.sin(time * 0.1) * 8f : 0f;
                draw(pose, buffers, light, overlay, st, part(id, "anim"), 8, 0, 8, Axis.XP, a);
            }
            case "swing" -> {
                float a = occupied(be) ? SeatEntity.swingAngle(time) : 0f;
                draw(pose, buffers, light, overlay, st, part(id, "anim"), 8, 30, 8, Axis.XP, a);
            }
            default -> { }
        }
        pose.popPose();
    }

    /** なめらかに回り始めて、なめらかに止まる */
    private static void spinTo(AnimBlockEntity be, double time, float target) {
        if (be.lastFrame < 0) be.lastFrame = (long) (time * 1000);
        double dt = Math.max(0, Math.min(0.5, (time * 1000 - be.lastFrame) / 1000.0));
        be.lastFrame = (long) (time * 1000);
        be.spinSpeed += (target - be.spinSpeed) * (float) Math.min(1, dt * 0.15);
        be.spin = (be.spin + be.spinSpeed * (float) dt) % 360f;
    }

    private static boolean occupied(AnimBlockEntity be) {
        AABB box = new AABB(be.getBlockPos()).inflate(1.5, 2, 1.5);
        return !be.getLevel().getEntitiesOfClass(SeatEntity.class, box, s -> !s.getPassengers().isEmpty()).isEmpty();
    }

    /** モデル座標の (px, py, pz) を中心に回して描く */
    private static void draw(PoseStack pose, MultiBufferSource buffers, int light, int overlay, BlockState st, ModelResourceLocation loc,
                             double px, double py, double pz, Axis axis, float deg) {
        BakedModel m = Minecraft.getInstance().getModelManager().getModel(loc);
        pose.pushPose();
        pose.translate(px / 16.0, py / 16.0, pz / 16.0);
        pose.mulPose(axis.rotationDegrees(deg));
        pose.translate(-px / 16.0, -py / 16.0, -pz / 16.0);
        Minecraft.getInstance().getBlockRenderer().getModelRenderer().renderModel(pose.last(), buffers.getBuffer(RenderType.cutout()),
                st, m, 1f, 1f, 1f, light, overlay, ModelData.EMPTY, RenderType.cutout());
        pose.popPose();
    }

    @Override
    public boolean shouldRenderOffScreen(AnimBlockEntity be) {
        return true;
    }

    public AABB getRenderBoundingBox(AnimBlockEntity be) {
        return new AABB(be.getBlockPos()).inflate(1, 2, 1);
    }
}
