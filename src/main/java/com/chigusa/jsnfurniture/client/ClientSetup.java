package com.chigusa.jsnfurniture.client;

import com.chigusa.jsnfurniture.JsnFurniture;
import com.chigusa.jsnfurniture.Spec;
import net.minecraft.client.renderer.entity.NoopRenderer;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.EntityRenderersEvent;
import net.neoforged.neoforge.client.event.ModelEvent;

@EventBusSubscriber(modid = JsnFurniture.MODID, bus = EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public final class ClientSetup {
    @SubscribeEvent
    public static void renderers(EntityRenderersEvent.RegisterRenderers e) {
        e.registerEntityRenderer(JsnFurniture.SEAT.get(), NoopRenderer::new);
        e.registerBlockEntityRenderer(JsnFurniture.DISPLAY_BE.get(), DisplayRenderer::new);
        e.registerBlockEntityRenderer(JsnFurniture.FURIN_BE.get(), FurinRenderer::new);
        e.registerBlockEntityRenderer(JsnFurniture.ANIM_BE.get(), AnimRenderer::new);
    }

    @SubscribeEvent
    public static void models(ModelEvent.RegisterAdditional e) {
        for (Spec s : Spec.ALL) {
            if (s.is("furin")) e.register(FurinRenderer.body(s.id()));
            for (String part : s.parts()) e.register(AnimRenderer.part(s.id(), part));
        }
    }

    private ClientSetup() {}
}
