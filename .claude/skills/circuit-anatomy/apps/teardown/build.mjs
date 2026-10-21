// Builds teardown.html: the page source with the anatomy kit inlined.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { kitScript } from "../../../anatomy/scripts/inline-kit.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const page = readFileSync(join(HERE, "page.src.html"), "utf8").replace("/*KIT*/", () => kitScript().replace(/<\/(script)/gi, "<\\/$1"));
writeFileSync(join(HERE, "teardown.html"), page);
console.log("wrote teardown.html", (page.length / 1024).toFixed(0) + " KB");
