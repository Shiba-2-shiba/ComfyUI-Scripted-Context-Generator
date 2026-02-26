import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "ComfyUI-Scripted-Context-Generator.PromptCleaner",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name === "PromptCleaner") {
            const onConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function (info) {
                // If the "text" widget has been converted to an input, the saved 
                // info.widgets_values length will be shorter than this.widgets.length,
                // causing a shift when ComfyUI restores them sequentially.
                if (info.inputs && info.widgets_values) {
                    let hasTextInput = false;
                    for (const input of info.inputs) {
                        if (input.name === "text") {
                            hasTextInput = true;
                            break;
                        }
                    }
                    
                    // If text is an input (forceInput) and the widgets_values are shifted
                    if (hasTextInput && this.widgets && info.widgets_values.length < this.widgets.length) {
                        // Unshift a dummy string value so the remaining widgets map to their correct slots
                        info.widgets_values.unshift("");
                    }
                }
                
                if (onConfigure) {
                    onConfigure.apply(this, arguments);
                }
            };
        }
    }
});
