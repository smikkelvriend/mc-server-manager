package nl.mcm;

import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.command.ConsoleCommandSender;
import org.bukkit.plugin.java.JavaPlugin;

import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;

/** Hulpplugin voor MC Server Manager: geeft de Tab-aanvullingen van de server door aan de console.
 *  Gebruik (alleen via de console):  mcmtab <id>            -> MCMTAB|id|<alle commando's, gescheiden door tab>
 *                                    mcmtab <id> <base64>   -> MCMTAB|id|<aanvullingen voor die regel> */
public class MCMTab extends JavaPlugin {
    @Override
    public void onEnable() {
        getLogger().info("MCMTab actief: MC Server Manager kan nu Tab-aanvullingen opvragen.");
    }

    private Object commandMap() throws Exception {
        Class<?> b = Class.forName("org.bukkit.Bukkit");
        try {
            return b.getMethod("getCommandMap").invoke(null);
        } catch (NoSuchMethodException e) {
            Object srv = b.getMethod("getServer").invoke(null);
            Method m = srv.getClass().getMethod("getCommandMap");
            m.setAccessible(true);
            return m.invoke(srv);
        }
    }

    @Override
    public boolean onCommand(CommandSender sender, Command cmd, String label, String[] args) {
        if (!(sender instanceof ConsoleCommandSender) || args.length < 1) return true;
        String id = args[0].replaceAll("[^A-Za-z0-9]", "");
        StringBuilder out = new StringBuilder("MCMTAB|").append(id).append('|');
        try {
            Object map = commandMap();
            Class<?> cm = Class.forName("org.bukkit.command.CommandMap");
            if (args.length == 1) {
                Map<?, ?> known = (Map<?, ?>) cm.getMethod("getKnownCommands").invoke(map);
                TreeSet<String> names = new TreeSet<>();
                for (Object k : known.keySet()) {
                    String s = String.valueOf(k);
                    if (!s.isEmpty() && s.indexOf(':') < 0) names.add(s);
                }
                out.append(String.join("\t", names));
            } else {
                String line = new String(Base64.getUrlDecoder().decode(args[1]), StandardCharsets.UTF_8);
                Method tc = cm.getMethod("tabComplete", CommandSender.class, String.class);
                Object r = tc.invoke(map, sender, line);
                List<String> list = new ArrayList<>();
                if (r instanceof List) for (Object o : (List<?>) r) list.add(String.valueOf(o).replace('\t', ' '));
                out.append(String.join("\t", list));
            }
        } catch (Throwable t) {
            out.append("!").append(t.getClass().getSimpleName());
        }
        sender.sendMessage(out.toString());
        return true;
    }
}
