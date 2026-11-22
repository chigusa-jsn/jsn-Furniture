package com.chigusa.jsnfurniture.client;

import com.chigusa.jsnfurniture.JsnFurniture;
import com.chigusa.jsnfurniture.block.FurinBlockEntity;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.client.renderer.blockentity.BlockEntityRendererProvider;
import net.minecraft.client.resources.model.BakedModel;
import net.minecraft.client.resources.model.ModelResourceLocation;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.neoforge.client.model.data.ModelData;

/** 風鈴の本体（ガラスと短冊）を、つり下げた点を中心にゆらす */
public class FurinRenderer implements BlockEntityRenderer<FurinBlockEntity> {
    public FurinRenderer(BlockEntityRendererProvider.Context ctx) {
    }

    public static ModelResourceLocation body(String id) {
        return ModelResourceLocation.standalone(ResourceLocation.fromNamespaceAndPath(JsnFurniture.MODID, "block/" + id + "_body"));
    }

    @Override
    public void render(FurinBlockEntity be, float partial, PoseStack pose, MultiBufferSource buffers, int light, int overlay) {
        if (be.getLevel() == null) return;
        String id = BuiltInRegistries.BLOCK.getKey(be.getBlockState().getBlock()).getPath();
        BakedModel model = Minecraft.getInstance().getModelManager().getModel(body(id));
        float t = be.getLevel().getGameTime() + partial;
        float since = t - be.ringAt;
        float wind = be.getLevel().isRaining() ? 6f : 3f;
        float amp = wind + (since >= 0 ? 16f * be.ringPower * (float) Math.exp(-since / 25.0) : 0);
        float a = (float) Math.sin(t * 0.21 + be.phase) * amp;
        float b = (float) Math.sin(t * 0.13 + be.phase * 1.7) * amp * 0.5f;
        pose.pushPose();
        pose.translate(0.5, 14 / 16.0, 0.5);
        pose.mulPose(Axis.ZP.rotationDegrees(a));
        pose.mulPose(Axis.XP.rotationDegrees(b));
        pose.translate(-0.5, -14 / 16.0, -0.5);
        Minecraft.getInstance().getBlockRenderer().getModelRenderer().renderModel(pose.last(), buffers.getBuffer(RenderType.translucent()),
                be.getBlockState(), model, 1f, 1f, 1f, light, overlay, ModelData.EMPTY, RenderType.translucent());
        pose.popPose();
    }
}
