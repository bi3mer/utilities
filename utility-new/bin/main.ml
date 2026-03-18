let lang = ref ""
let desc = ref ""
let name = ref ""

let speclist =
  [
    ("-l", Arg.Set_string lang, "Language to scaffold (c, ocaml, python)");
    ("-d", Arg.Set_string desc, "One-line description");
  ]

let usage = "Usage: utility-new <name> -l <lang> [-d <desc>]"

let rec dirname_n path n =
  if n <= 0 then path else dirname_n (Filename.dirname path) (n - 1)

let () =
  Arg.parse speclist (fun anon -> name := anon) usage;
  if !name = "" then (
    print_endline usage;
    exit 1);

  (match !lang with
  | "c" | "python" | "ocaml" -> ()
  | "" ->
      Printf.eprintf "Error: -l <lang> is required\n";
      exit 1
  | other ->
      Printf.eprintf "Error: unknown language '%s'\n" other;
      exit 1);

  let root = dirname_n (Unix.realpath Sys.executable_name) 5 in
  let dir = Filename.concat root ("utility-" ^ !name) in
  if Sys.file_exists dir then
    Printf.eprintf "Error: utility '%s' already exists\n%!" !name (* exit 1 *)
  else Unix.mkdir dir 0o755;

  match !lang with
  | "c" | "python" -> ()
  | "ocaml" ->
      print_endline "Building ocaml project...";

      Unix.symlink "../default-configs/.ocamlformat"
        (Filename.concat dir ".ocamlformat");

      let f = open_out (Filename.concat dir "dune-project") in
      output_string f "hello, world!\n";
      close_out f;

      (* let oc = open_out "path/to/file" in output_string oc "hello world\n";
         close_out oc *)
      let bindir = Filename.concat dir "bin" in
      Unix.mkdir bindir 0o755
  | _ -> assert false
