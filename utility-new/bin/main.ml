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

let copyfile src dst =
  let src_f = open_in src in
  let content = In_channel.input_all src_f in
  close_in src_f;

  let dst_f = open_out dst in
  output_string dst_f content;
  close_out dst_f

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

  let uname = "utility-" ^ !name in
  let root = dirname_n (Unix.realpath Sys.executable_name) 5 in
  let dir = Filename.concat root uname in
  if Sys.file_exists dir then (
    Printf.eprintf "Error: utility '%s' already exists\n%!" uname;
    exit 1)
  else Unix.mkdir dir 0o755;

  match !lang with
  | "c" -> ()
  | "python" ->
      print_endline "Building python project...";
      let src_dir = Filename.concat dir "src" in
      Unix.mkdir src_dir 0o755;

      copyfile
        (Filename.concat root (Filename.concat "default-configs" "main.py"))
        (Filename.concat src_dir "main.py");

      let module_name =
        String.map (fun c -> if c = '-' then '_' else c) !name
      in
      let f = open_out (Filename.concat dir "pyproject.toml") in
      output_string f
        (Printf.sprintf
           {|[build-system]
      requires = ["setuptools>=68.0"]
      build-backend = "setuptools.build_meta"

      [tool.setuptools]
      py-modules = ["%s"]
      package-dir = {"" = "src"}

      [project]
      name = "%s"
      version = "0.1.0"
      description = ""
      requires-python = ">=3.10"
      dependencies = []

      [project.scripts]
      %s = "%s:main"
  |}
           module_name module_name uname module_name);
      close_out f;

      print_endline "Done!"
  | "ocaml" ->
      print_endline "Building ocaml project...";

      Unix.symlink "../default-configs/.ocamlformat"
        (Filename.concat dir ".ocamlformat");

      (let f = open_out (Filename.concat dir "dune-project") in
       output_string f "(lang dune 3.0)\n";
       output_string f ("(name " ^ uname ^ ")");
       close_out f);

      let bindir = Filename.concat dir "bin" in
      Unix.mkdir bindir 0o755;

      (let f = open_out (Filename.concat bindir "dune") in
       output_string f
         (Printf.sprintf
            {|(executable
  (public_name %s)
  (name main)
  (libraries unix))
|}
             uname);
       close_out f);

      copyfile
        (Filename.concat root (Filename.concat "default-configs" "main.ml"))
        (Filename.concat bindir "main.ml");

      (let f = open_out (Filename.concat dir (uname ^ ".opam")) in
       close_out f);

      print_endline "Done!"
  | _ -> assert false
